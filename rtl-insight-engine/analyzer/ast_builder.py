"""
AST Builder — builds a signal dependency graph using NetworkX.
"""

import networkx as nx
from typing import Dict, List, Tuple
from .parser import ParsedRTL, Signal

class DependencyGraph:

    def __init__(self, rtl: ParsedRTL):
        self.rtl = rtl
        self.graph = nx.DiGraph()
        self._build()

    def _build(self):
        # Add all signal nodes
        for name, sig in self.rtl.signals.items():
            self.graph.add_node(name, **{
                'signal_type': sig.signal_type,
                'width': sig.width,
                'clock_domain': sig.clock_domain
            })

        # Add edges from operations: rhs_signal → lhs
        for op in self.rtl.operations:
            if op.lhs not in self.graph:
                self.graph.add_node(op.lhs, signal_type='unknown', width=1)
            for src in op.rhs_signals:
                if src not in self.graph:
                    self.graph.add_node(src, signal_type='unknown', width=1)
                if src != op.lhs:
                    self.graph.add_edge(src, op.lhs, operator=op.operator)

    def get_fanout(self, signal: str) -> int:
        """Number of signals directly driven by this signal."""
        return self.graph.out_degree(signal) if signal in self.graph else 0

    def get_fanin(self, signal: str) -> int:
        """Number of signals driving this signal."""
        return self.graph.in_degree(signal) if signal in self.graph else 0

    def get_downstream_signals(self, signal: str) -> List[str]:
        """All signals reachable downstream from this signal."""
        if signal not in self.graph:
            return []
        return list(nx.descendants(self.graph, signal))

    def get_upstream_signals(self, signal: str) -> List[str]:
        """All signals this signal depends on."""
        if signal not in self.graph:
            return []
        return list(nx.ancestors(self.graph, signal))

    def get_all_paths(self, src: str, dst: str) -> List[List[str]]:
        try:
            return list(nx.all_simple_paths(self.graph, src, dst, cutoff=10))
        except Exception:
            return []

    def get_critical_nodes(self) -> List[Tuple[str, int]]:
        """Signals with highest betweenness centrality (most critical paths)."""
        if len(self.graph.nodes) < 3:
            return [(n, 0) for n in self.graph.nodes]
        centrality = nx.betweenness_centrality(self.graph)
        return sorted(centrality.items(), key=lambda x: x[1], reverse=True)