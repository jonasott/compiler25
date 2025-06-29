from assembly.common import *
import assembly.tac_ast as tac
import common.log as log
from common.prioQueue import PrioQueue

def chooseColor(x: tac.ident, forbidden: dict[tac.ident, set[int]]) -> int:
    """
    Returns the lowest possible color for variable x that is not forbidden for x.
    """
    color = 0
    while color in forbidden[x]:
      color += 1
    return color

def colorInterfGraph(g: InterfGraph, secondaryOrder: dict[tac.ident, int]={},
                     maxRegs: int=MAX_REGISTERS) -> RegisterMap:
    """
    Given an interference graph, computes a register map mapping a TAC variable
    to a TACspill variable. You have to implement the "simple graph coloring algorithm"
    from slide 58 here.

    - Parameter maxRegs is the maximum number of registers we are allowed to use.
    - Parameter secondaryOrder is used by the tests to get deterministic results even
      if two variables have the same number of forbidden colors.
    """
    log.debug(f"Coloring interference graph with maxRegs={maxRegs}")
    colors: dict[tac.ident, int] = {}
    forbidden: dict[tac.ident, set[int]] = {v: set() for v in g.vertices}
    q = PrioQueue(secondaryOrder)
    
    for v in g.vertices:
        q.push(v)
    
    while not q.isEmpty():
      v = q.pop()
      
      color = chooseColor(v, forbidden)
      colors[v] = color
      for v2 in g.succs(v):
        forbidden[v2].add(color)
        q.incPrio(v2)
    
    m = RegisterAllocMap(colors, maxRegs)
    return m
