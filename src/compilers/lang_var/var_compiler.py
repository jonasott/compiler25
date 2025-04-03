from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *
import common.utils as utils

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
    return []

def compileAssign(var: ident, right: exp) -> list[WasmInstr]:
    return compileExp(right) + [WasmInstrVarLocal("set", identToWasmId(var))]


def identToWasmId(ident: ident) -> WasmId:
    return WasmId(f"${ident.name}")