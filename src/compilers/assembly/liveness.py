from assembly.common import *
from assembly.graph import Graph
import assembly.tac_ast as tac

def instrDef(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers defined by some instrucution.
    """
    match instr:
        case tac.Assign(x,_):
            return set([x])
        case tac.Call(x,tac.Ident("$input_i64"),_):
            if x is not None:
                return set([x])
            return set()
        case _:
            return set()
            
            

def instrUse(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers used by some instrucution.
    """
    match instr:
        case tac.Assign(_,e):
            return instrUseExp(e)
        case tac.Call(_,_,args):
            r: set[tac.ident] = set()
            for arg in args:
                r = r.union(instrUsePrim(arg))
            return r
        case tac.GotoIf(p,_):
            return instrUsePrim(p)
        case _:
            return set()
            
            
def instrUseExp(exp: tac.exp) -> set[tac.ident]:
    match exp:
        case tac.Prim(p):
            return instrUsePrim(p)
        case tac.BinOp(l,_,r):
            return instrUsePrim(l).union(instrUsePrim(r))

def instrUsePrim(prim: tac.prim) -> set[tac.ident]:
    match prim:
        case tac.Const(_):
            return set()
        case tac.Name(x):
            return set([x])

# Each individual instruction has an identifier. This identifier is the tuple
# (index of basic block, index of instruction inside the basic block)
type InstrId = tuple[int, int]

class InterfGraphBuilder:
    def __init__(self):
        # self.before holds, for each instruction I, to set of variables live before I.
        self.before: dict[InstrId, set[tac.ident]] = {}
        # self.after holds, for each instruction I, to set of variables live after I.
        self.after: dict[InstrId, set[tac.ident]] = {}

    def liveStart(self, bb: BasicBlock, s: set[tac.ident]) -> set[tac.ident]:
        """
        Given a set of variables s and a basic block bb, liveStart computes
        the set of variables live at the beginning of bb, assuming that s
        are the variables live at the end of the block.

        Essentially, you have to implement the subalgorithm "Computing L_start" from
        slide 46 here. You should update self.after and self.before while traversing
        the instructions of the basic block in reverse.
        """
        n = len(bb.instrs) - 1

        if len(bb.instrs) == 0:
            return set()
        
        for i in range(n, -1, -1):
            instr = bb.instrs[i]
            if i == n:
                self.after[(bb.index,i)] = s
            else:
                self.after[(bb.index,i)] = self.before[(bb.index,i+1)]
                
            self.before[(bb.index, i)] = self.after[(bb.index, i)].difference(instrDef(instr)).union(instrUse(instr))
        return self.before[(bb.index, 0)]

    def liveness(self, g: ControlFlowGraph):
        """
        This method computes liveness information and fills the sets self.before and
        self.after.

        You have to implement the algorithm for computing liveness in a CFG from
        slide 46 here.
        """
        
        insets: dict[int, set[tac.ident]] = {v: set() for v in g.vertices}
        insets_before: dict[int,set[tac.ident]] = {}
        
        while insets != insets_before:
            insets_before = insets.copy()
            for vertex in g.vertices: 
                out: set[tac.ident] = set()
                
                for bs in g.succs(vertex):
                    out = out.union(insets[bs])
                
                insets[vertex] = self.liveStart(g.getData(vertex), out)
        

    def __addEdgesForInstr(self, instrId: InstrId, instr: tac.instr, interfG: InterfGraph):
        """
        Given an instruction and its ID, adds the edges resulting from the instruction
        to the interference graph.

        You should implement the algorithm specified on the slide
        "Computing the interference graph" (slide 50) here.
        """
        for x in instrDef(instr):
            for y in self.after[instrId]:
                if x == y:
                    continue
                match instr:
                    case tac.Assign(ident, right):
                        match right:
                            case tac.Prim(p):
                                match p:
                                    case tac.Name(var):
                                        if x == ident and y == var:
                                            continue
                                    case _:
                                        pass
                            case _:
                                pass
                    case _:
                        pass
                interfG.addEdge(x,y)

    def build(self, g: ControlFlowGraph) -> InterfGraph:
        """
        This method builds the interference graph. It performs three steps:

        - Use liveness to fill the sets self.before and self.after.
        - Setup the interference graph as an undirected graph containing all variables
          defined or used by any instruction of any basic block. Initially, the
          graph does not have any edges.
        - Use __addEdgesForInstr to fill the edges of the interference graph.
        """
        self.liveness(g)
        
        interfGraph: InterfGraph = Graph(kind="undirected")
        
        for vertex in g.vertices:
            block: BasicBlock = g.getData(vertex)
            for instr in block.instrs:
                vars = instrUse(instr).union(instrDef(instr))
                for var in vars:
                    if not interfGraph.hasVertex(var):
                        interfGraph.addVertex(var, None)
        
        for vertex in g.vertices:
            block:BasicBlock = g.getData(vertex)
            for i,instr in enumerate(block.instrs):
                self.__addEdgesForInstr((block.index,i),instr,interfGraph)
        
        return interfGraph

def buildInterfGraph(g: ControlFlowGraph) -> InterfGraph:
    builder = InterfGraphBuilder()
    return builder.build(g)
