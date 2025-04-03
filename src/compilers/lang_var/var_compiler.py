from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = var_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64') for x in vars]
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
        case Assign(var, right):
            return compileAssign(var, right)
        
def compileExp(exp: exp) -> list[WasmInstr]:
    match exp:
        case IntConst(value):
            return [WasmInstrConst("i64",value)]
        case Name(name):
            return [WasmInstrVarLocal("get", identToWasmId(name))]
        case Call(name, args):
            return compileCall(name, args)
        case UnOp(op, arg):
            return compileUnOp(op, arg)
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
    
    return [ce for e in args for ce in compileExp(e)] + [WasmInstrCall(identToWasmId(i))]

def compileUnOp(op: unaryop, arg: exp) -> list[WasmInstr]:
    match op:
        case USub():
            return [WasmInstrConst("i64",0)] + compileExp(arg) + [WasmInstrNumBinOp("i64","sub")]

def compileBinOp(left: exp, op: binaryop, right: exp) -> list[WasmInstr]:
    match op:
        case Add():
            return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp("i64", "add")]
        case Sub():
            return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp("i64", "sub")]
        case Mul():
            return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp("i64", "mul")]
        

def compileAssign(var: ident, right: exp) -> list[WasmInstr]:
    return compileExp(right) + [WasmInstrVarLocal("set", identToWasmId(var))]


def identToWasmId(ident: ident) -> WasmId:
    return WasmId(f"${ident.name}")