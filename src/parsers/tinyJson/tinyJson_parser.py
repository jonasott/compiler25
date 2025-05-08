from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleJson(toks: TokenStream) -> Json:
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt])

def ruleObject(toks: TokenStream) -> dict[str, Json]:
    toks.ensureNext("LBRACE")
    d = ruleEntryList(toks)
    toks.ensureNext("RBRACE")
    return d

def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    if toks.lookahead().type == "STRING":
        return ruleEntryListNotEmpty(toks)
    else:
        return {}

def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    d : dict[str,Json] = {}
    e = ruleEntry(toks)
    d.update([e])
    if toks.lookahead().type == "COMMA":
        toks.next()
        d.update(ruleEntryListNotEmpty(toks))
    return d

def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    s = ruleString(toks)
    toks.ensureNext("COLON")
    return (s, ruleJson(toks))

def ruleString(toks: TokenStream) -> str:
    return str(toks.ensureNext("STRING").value[1:-1])

def ruleInt(toks: TokenStream) -> int:
    return int(toks.ensureNext("INT").value)

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res
