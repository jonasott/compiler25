from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as loop_tychecker
from lang_loop.loop_tychecker import *
from common.compilerSupport import *

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = loop_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(id), "i64" if type(ty) == Int else "i32") for id,ty in vars.types()]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)])

    
def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    out: list[WasmInstr] = []
    
    for stmt in stmts:
        out += compileStmt(stmt)
    
    return out

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
 
def compileWhile(cond: exp, body: list[stmt]) -> list[WasmInstr]:
    return [WasmInstrBlock(WasmId("$loop_0_exit"), None,
                           [WasmInstrLoop(WasmId("$loop_0_start"), compileWhileBody(cond, body))]
                           )]

def compileWhileBody(cond: exp, body: list[stmt]) -> list[WasmInstr]:
    out : list[WasmInstr] = []
    out.extend(compileExp(cond))
    out.append(WasmInstrIf(None,[], [WasmInstrBranch(WasmId("$loop_0_exit"), False)]))
    out.extend(compileStmts(body))
    out.append(WasmInstrBranch(WasmId("$loop_0_start"),False))
    return out

def compileIf(cond: exp, thenBody: list[stmt], elseBody: list[stmt]) -> list[WasmInstr]:
    return compileExp(cond) + [WasmInstrIf(None,compileStmts(thenBody),compileStmts(elseBody))]

def compileExps(exps: list[exp]) -> list[WasmInstr]:
    out : list[WasmInstr] = []
    for e in exps:
        out.extend(compileExp(e))
    return out
 
def compileExp(exp: exp) -> list[WasmInstr]:
    match exp:
        case IntConst(value):
            return [WasmInstrConst("i64", value)]
        case BoolConst(value):
            return [WasmInstrConst("i32", value)]
        case Name(name):
            return [WasmInstrVarLocal("get", identToWasmId(name))]
        case Call(name, args):
            return compileCall(name,args)
        case UnOp(op, arg):
            return compileUnOp(op,arg)
        case BinOp(left, op, right):
            return compileBinOp(left, op, right)
        
def compileCall(name: ident, args: list[exp]) -> list[WasmInstr]:
    i = Ident("")
    match name.name:
        case "print":
            i = Ident("print_i64")
        case "input_int":
            i = Ident("input_i64")
        case _:
            pass
    
    return compileExps(args) + [WasmInstrCall(identToWasmId(i))]

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
        case And():
            return [] #if shit
        case Or():
            return []
        
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