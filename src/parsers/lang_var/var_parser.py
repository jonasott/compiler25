from lark import ParseTree
from lang_var.var_ast import *
from parsers.common import *
import common.log as log

grammarFile = "./src/parsers/lang_var/var_grammar.lark"

def parse(args: ParserArgs) -> exp:
    parseTree = parseAsTree(args, grammarFile, 'lvar')
    ast = parseTreeToExpAst(parseTree)
    log.debug(f'AST: {ast}')
    return ast

def parseTreeToExpAst(t: ParseTree) -> exp:
    match t.data:
        case 'int_exp':
            return IntConst(int(asToken(t.children[0])))
        case 'add_exp':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Add(), parseTreeToExpAst(e2))
        case 'mul_exp':
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Mul(), parseTreeToExpAst(e2))
        case 'exp_1' | 'exp_2' | 'paren_exp':
            return parseTreeToExpAst(asTree(t.children[0]))
        case "sub_exp":
            e1, e2 = [asTree(c) for c in t.children]
            return BinOp(parseTreeToExpAst(e1), Sub(), parseTreeToExpAst(e2))
        case "neg_exp":
            e: Any[Token | Tree[Token]] = t.children[0]
            return UnOp(USub(), parseTreeToExpAst(e))
        case "function_call":
            i: Any[Token | Tree[Token]] = t.children[0]
            e: Any[Token | Tree[Token]] = t.children[1:]
            e = [parseTreeToExpAst(x) for x in e]
            return Call(Ident(i.value),e)
        case "var_exp":
            e: Any[Token | Tree[Token]] = t.children[0]
            return Name(Ident(e.value))
        case kind:
            raise Exception(f'unhandled parse tree of kind {kind} for exp: {t}')
        
        
def parseModule(args: ParserArgs) -> mod:
    parseTree = parseAsTree(args, grammarFile, "lvar")
    ast = parseTreeToModuleAst(parseTree)
    log.debug(f"Module AST:: {ast}")
    return ast

def parseTreeToStmtAst(t : ParseTree) -> stmt:
    match t.data:
        case "assign_stmt":
            e: Any[Token | Tree[Token]] = t.children[0]
            return Assign(Ident(e.children[0].value), parseTreeToExpAst(asTree(t.children[1])))
        case "exp_stmt":
            return StmtExp(parseTreeToExpAst(asTree(t.children[0])))
        case kind:
            raise Exception(f"unhandled parse tree of kind {kind} for stmt: {t}")

def parseTreeToStmtListAst(t: ParseTree) -> list[stmt]:
    stmt_list : list[stmt] = []
    for child in t.children:
        stmt_list.append(parseTreeToStmtAst(asTree(child)))
    return stmt_list

def parseTreeToModuleAst(t: ParseTree) -> mod:
    stmt_list = parseTreeToStmtListAst(asTree(t))
    return Module(stmt_list)