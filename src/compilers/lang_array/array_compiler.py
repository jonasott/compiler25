from lang_array.array_astAtom import *
import lang_array.array_ast as plainAst
from common.wasm import *
import lang_array.array_tychecker as array_tychecker
import lang_array.array_transform as array_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *

config: CompilerConfig

def compileModule(m: plainAst.mod, cfg: CompilerConfig) -> WasmModule:
    global config
    config = cfg
    vars = array_tychecker.tycheckModule(m)
    ctx = array_transform.Ctx()
    stmts = array_transform.transStmts(m.stmts, ctx)
    instrs = compileStmts(stmts)
    idMain = WasmId("$main")
    
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(id), "i64" if type(ty) == Int else "i32") for id,ty in vars.types()]
    freshLocals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(id), "i64" if type(ty) == Int else "i32") for id,ty in ctx.freshVars.items()]
    locals += freshLocals
    locals += Locals.decls()
    
    return WasmModule(
        imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=Globals.decls(),
        data=Errors.data(),
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals,instrs)])
    
def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    res: list[WasmInstr] = []
    
    for stmt in stmts:
        res += compileStmt(stmt)
    
    return res

def compileStmt(stmt: stmt) -> list[WasmInstr]:
    match stmt:
        case StmtExp(exp):
            return compileExp(exp)
        case Assign(ident, exp):
            return compileAssign(ident, exp)
        case IfStmt(cond, thenBody, elseBody):
            return compileIf(cond, thenBody, elseBody)
        case WhileStmt(cond, body):
            return compileWhile(cond, body)
        case SubscriptAssign(left,index,right):
            return compileSubscriptAssign(left,index,right)
        

def compileWhile(cond: exp, body: list[stmt]) -> list[WasmInstr]:
    return [WasmInstrBlock(WasmId("$loop_0_exit"), None,
                           [WasmInstrLoop(WasmId("$loop_0_start"), compileWhileBody(cond, body))]
                           )]

def compileWhileBody(cond: exp, body: list[stmt]) -> list[WasmInstr]:
    res : list[WasmInstr] = []
    res += compileExp(cond)
    res += [WasmInstrIf(None,[], [WasmInstrBranch(WasmId("$loop_0_exit"), False)])]
    res += compileStmts(body)
    res += [WasmInstrBranch(WasmId("$loop_0_start"),False)]
    return res

def compileIf(cond: exp, thenBody: list[stmt], elseBody: list[stmt]) -> list[WasmInstr]:
    return compileExp(cond) + [WasmInstrIf(None,compileStmts(thenBody),compileStmts(elseBody))]

def compileExps(exps: list[exp]) -> list[WasmInstr]:
    res : list[WasmInstr] = []
    for e in exps:
        res += compileExp(e)
    return res
 
def compileExp(exp: exp) -> list[WasmInstr]:
    match exp:
        case AtomExp(atomExp):
            return compileAtomicExp(atomExp)
        case Call(name, args):
            return compileCall(name,args)
        case UnOp(op, arg):
            return compileUnOp(op,arg)
        case BinOp(left, op, right):
            return compileBinOp(left, op, right)
        case ArrayInitDyn(len, elemInit):
            return compileArrayInitDyn(len, elemInit)
        case ArrayInitStatic(elemInit):
            return compileArrayInitStatic(elemInit)
        case Subscript(array, index):
            return compileSubscript(array, index)
        
def compileArrayInitDyn(len: atomExp, elemInit: atomExp) -> list[WasmInstr]:
    res: list[WasmInstr] = []
    elementSize = 8 if asTy(elemInit.ty) == Int() else 4
    dtype: WasmValtype = "i64" if asTy(elemInit.ty) == Int() else "i32"

    whileBody: list[WasmInstr] = [
        WasmInstrVarLocal("get",Locals.tmp_i32),
        WasmInstrVarGlobal("get", Globals.freePtr),
        WasmInstrIntRelOp("i32","lt_u"),
        WasmInstrIf(None,[],[
            WasmInstrBranch(identToWasmId(Ident("loop_exit")),False)
            ]),
        WasmInstrVarLocal("get",Locals.tmp_i32)
    ]
    whileBody += compileAtomicExp(elemInit)
    whileBody += [
        WasmInstrMem(dtype,"store"),
        WasmInstrVarLocal("get",Locals.tmp_i32),
        WasmInstrConst("i32", elementSize),
        WasmInstrNumBinOp("i32", "add"),
        WasmInstrVarLocal("set",Locals.tmp_i32),
        WasmInstrBranch(identToWasmId(Ident("loop_start")), False)
    ]

    res += compileInitArray(len, asTy(elemInit.ty))
    res += [
        WasmInstrVarLocal("tee", Locals.tmp_i32),
        WasmInstrVarLocal("get", Locals.tmp_i32),
        WasmInstrConst("i32",4),
        WasmInstrNumBinOp("i32","add"),
        WasmInstrVarLocal("set", Locals.tmp_i32),
        WasmInstrBlock(identToWasmId(Ident("loop_exit")),None,[
            WasmInstrLoop(identToWasmId(Ident("loop_start")),whileBody)
        ])
    ]
    
    return res

def compileArrayInitStatic(elemInit: list[atomExp]) -> list[WasmInstr]:
    res: list[WasmInstr] = []
    elementSize = 8 if asTy(elemInit[0].ty) == Int() else 4
    dtype = "i64" if asTy(elemInit[0].ty) == Int() else "i32"
    
    res += compileInitArray(IntConst(len(elemInit)), asTy(elemInit[0].ty))
    for index, elem in enumerate(elemInit):
        offset = 4 + elementSize * index
        res += [
            WasmInstrVarLocal("tee", Locals.tmp_i32),
            WasmInstrVarLocal("get", Locals.tmp_i32),
            WasmInstrConst("i32", offset),
            WasmInstrNumBinOp("i32","add"),
        ]
        res += compileAtomicExp(elem) + [WasmInstrMem(dtype,"store")]
    return res
        
def compileSubscript(array: atomExp, index: atomExp) -> list[WasmInstr]:
    res: List[WasmInstr] = []
    res += arrayOffsetInstrs(array, index)
    if asTy(array.ty) == Int():
        res += [WasmInstrMem("i64","load")]
    else:
        res += [WasmInstrMem("i32","load")]
    
    return res

def compileSubscriptAssign(left: atomExp, index: atomExp, right: exp) -> list[WasmInstr]:
    res: List[WasmInstr] = []
    res += arrayOffsetInstrs(left, index)
    
    res += compileExp(right)
    
    match right.ty:
        case NotVoid(ty):
            match ty:
                case Int():
                    res += [WasmInstrMem("i64","store")]
                case _:
                    res += [WasmInstrMem("i32","store")]
        case _:
            pass
    
    return res
 
def arrayOffsetInstrs(array: atomExp, index: atomExp) -> list[WasmInstr]:
    res: List[WasmInstr] = []
    
    #check index < 0
    res += compileAtomicExp(index)
    res += [
        WasmInstrConvOp("i32.wrap_i64"),
        WasmInstrConst("i32",0),
        WasmInstrIntRelOp("i32","lt_s"),
        WasmInstrIf(None,Errors.outputError(Errors.arraySize) + [WasmInstrTrap()],[])
    ]
    
    res += compileAtomicExp(array)
    res += arrayLenInstrs()
    #check length < max
    res += compileAtomicExp(index)
    res += [
        WasmInstrConvOp("i32.wrap_i64"),
        WasmInstrIntRelOp("i32","lt_s"),
        WasmInstrIf(None, Errors.outputError(Errors.arraySize) + [WasmInstrTrap()],[])
    ]
    
    res += compileAtomicExp(array)
    res += compileAtomicExp(index)
    
    res += [
        WasmInstrConvOp("i32.wrap_i64"),
    ]
    
    return res
    
    

def compileInitArray(len: atomExp, elemInitType: ty) -> list[WasmInstr]:
    res: list[WasmInstr] = []
    
    elementSize = 8 if elemInitType == Int() else 4
    headerVal = 1 if elemInitType == Int() or elemInitType == Bool() else 3
    
    #check length > 0
    res += compileLength(len)
    res += [
        WasmInstrConst("i32",0),
        WasmInstrIntRelOp("i32","lt_s"),
        WasmInstrIf(None,Errors.outputError(Errors.arraySize) + [WasmInstrTrap()],[])
    ]
    
    #check length < max
    res += compileLength(len)
    res += [
        WasmInstrConst("i32", elementSize),
        WasmInstrNumBinOp("i32","mul"),
        WasmInstrConst("i32", config.maxArraySize),
        WasmInstrIntRelOp("i32","gt_s"),
        WasmInstrIf(None, Errors.outputError(Errors.arraySize) + [WasmInstrTrap()],[])
    ]
    
    res += [WasmInstrVarGlobal("get", Globals.freePtr)]
            
    #compute header value
    res += compileLength(len)
    res += [
        WasmInstrConst("i32", 4),
        WasmInstrNumBinOp("i32","shl"),
        WasmInstrConst("i32",headerVal),
        WasmInstrNumBinOp("i32","xor")
    ]
    
    #store header
    res += [
        WasmInstrMem("i32", "store")
    ]
    
    #move free pointer and return array address
    res += [WasmInstrVarGlobal("get", Globals.freePtr)]
    res += compileLength(len)
    res += [
        WasmInstrConst("i32", elementSize),
        WasmInstrNumBinOp("i32","mul"),
        WasmInstrConst("i32",4),
        WasmInstrNumBinOp("i32","add"),
        WasmInstrVarGlobal("get",Globals.freePtr),
        WasmInstrNumBinOp("i32","add"),
        WasmInstrVarGlobal("set",Globals.freePtr)
    ]
    
    return res

#compile length expression and wrap in i32
def compileLength(len: atomExp) -> list[WasmInstr]:
    return compileAtomicExp(len) + [WasmInstrConvOp("i32.wrap_i64")]
        
def compileAtomicExp(atomExp: atomExp) -> list[WasmInstr]:
    match atomExp:
        case IntConst(value):
            return [WasmInstrConst("i64",value)]
        case BoolConst(value):
            match value:
                case True:
                    return [WasmInstrConst("i32",1)]
                case False:
                    return [WasmInstrConst("i32",0)]
        case Name(name):
            return [WasmInstrVarLocal("get", identToWasmId(name))]
    
def compileCall(name: ident, args: list[exp]) -> list[WasmInstr]:
    i = Ident("")
    match name.name:
        case "print":
            if (tyOfExp(args[0]) == Int()):
                i = Ident("print_i64")
            else:
                i = Ident("print_bool")
        case "input_int":
            i = Ident("input_i64")
        case "len":
            return compileLenCall(args)
        case _:
            raise Exception(f"CALL {name.name}")
    
    return compileExps(args) + [WasmInstrCall(identToWasmId(i))]
    
def compileLenCall(args: list[exp]) -> list[WasmInstr]:
    res: list[WasmInstr] = []
    res += compileExps(args)
    res += arrayLenInstrs()
    
    return res
    
def arrayLenInstrs() -> list[WasmInstr]:
    return [
        WasmInstrMem("i32", "load"),
        WasmInstrConst("i32", 4),
        WasmInstrNumBinOp("i32","shr_u"),
        WasmInstrConvOp("i64.extend_i32_u")
    ]

def compileUnOp(op: unaryop, arg: exp) -> list[WasmInstr]:
    match op:
        case USub():
            return [WasmInstrConst("i64", 0)] + compileExp(arg) + [WasmInstrNumBinOp("i64","sub")]
        case Not():
            return [WasmInstrConst("i32",1)] + compileExp(arg) + [WasmInstrNumBinOp("i32","sub")]
            

def compileBinOp(left: exp, op: binaryop, right: exp) -> list[WasmInstr]:
    expressions : list[WasmInstr] = compileExp(left) + compileExp(right)
    instr: list[WasmInstr]
    match op:
        case Add():
            instr = [WasmInstrNumBinOp("i64", "add")]
        case Sub():
            instr = [WasmInstrNumBinOp("i64","sub")]
        case Mul():
            instr = [WasmInstrNumBinOp("i64","mul")]
        case Less():
            instr = [WasmInstrIntRelOp("i64","lt_s")]
        case LessEq():
            instr = [WasmInstrIntRelOp("i64","le_s")]
        case Greater():
            instr = [WasmInstrIntRelOp("i64","gt_s")]
        case GreaterEq():
            instr = [WasmInstrIntRelOp("i64","ge_s")]
        case Eq():
            if tyOfExp(left) == Int():
                instr = [WasmInstrIntRelOp("i64","eq")]
            else:
                instr = [WasmInstrIntRelOp("i32","eq")]
        case NotEq():
            if tyOfExp(left) == Int():
                instr = [WasmInstrIntRelOp("i64","ne")]
            else:
                instr = [WasmInstrIntRelOp("i32","ne")]
        case Is():
            instr = [WasmInstrIntRelOp("i32","eq")]
        case And():
            return compileExp(left) + [WasmInstrIf("i32",compileExp(right), [WasmInstrConst("i32",0)])]
        case Or():
            return compileExp(left) + [WasmInstrIf("i32",[WasmInstrConst("i32",1)], compileExp(right))]
        
    return expressions + instr
    

def compileAssign(var: ident, right: exp) -> list[WasmInstr]:
    return compileExp(right) + [WasmInstrVarLocal("set", identToWasmId(var))]


def tyOfExp(e : exp) -> ty:
    match e.ty:
        case None:
            raise CompileError.typeError(f"Invalid type {e.ty}")
        case Void():
            raise CompileError.typeError(f"Invalid type {e.ty}")
        case NotVoid(ety):
            return ety
    
    
def identToWasmId(ident: ident) -> WasmId:
    return WasmId(f"${ident.name}")

def asTy(ty: Optional[ty]) -> ty:
    assert ty is not None
    return ty
    