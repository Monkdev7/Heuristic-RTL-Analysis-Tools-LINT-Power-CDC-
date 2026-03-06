"""
Metrics Engine — computes all 5 RTL metrics per signal/operation.
"""

import math
from typing import Dict, List
from .parser import ParsedRTL, Signal, Operation
from .ast_builder import DependencyGraph

OPERATOR_COMPLEXITY = {
    'ADD': 0.7, 'SUB': 0.7,
    'MUL': 0.9, 'DIV': 0.95,
    'AND': 0.4, 'OR': 0.4, 'XOR': 0.5,
    'SHIFT_RIGHT': 0.5, 'SHIFT_LEFT': 0.5,
    'COMPARE': 0.3, 'TERNARY': 0.6,
    'ASSIGN': 0.2, 'UNKNOWN': 0.5
}

class MetricsEngine:

    def __init__(self, rtl: ParsedRTL, graph: DependencyGraph):
        self.rtl = rtl
        self.graph = graph
        self.total_signals = max(len(rtl.signals), 1)

    # ─── Metric 1: Initial Weight ──────────────────────────────────────────
    def initial_weight(self, signal: Signal) -> float:
        """
        Importance of a signal based on type and bit-width.
        Higher = more important to the design.
        """
        type_weight = {
            'input': 0.8, 'output': 0.9, 'output reg': 0.9,
            'reg': 0.6, 'wire': 0.5, 'unknown': 0.4
        }
        base = type_weight.get(signal.signal_type, 0.5)

        # Narrow signals (flags) are critical: zero, carry, overflow
        if signal.width == 1:
            width_factor = 1.0
        elif signal.width <= 4:
            width_factor = 0.85
        elif signal.width <= 16:
            width_factor = 0.7
        else:
            width_factor = 0.55

        return round(base * width_factor, 4)

    # ─── Metric 2: Impact Score ────────────────────────────────────────────
    def impact_score(self, signal_name: str) -> float:
        """
        How many downstream signals are affected if this signal fails.
        Normalized by total signal count.
        """
        downstream = self.graph.get_downstream_signals(signal_name)
        raw = len(downstream) / self.total_signals
        # Boost for output signals
        sig = self.rtl.signals.get(signal_name)
        if sig and 'output' in sig.signal_type:
            raw = min(1.0, raw * 1.3)
        return round(min(raw, 1.0), 4)

    # ─── Metric 3: Susceptibility ──────────────────────────────────────────
    def susceptibility(self, signal_name: str) -> float:
        """
        How many upstream signals can corrupt this signal.
        More inputs = more vulnerable.
        """
        fanin = self.graph.get_fanin(signal_name)
        upstream = self.graph.get_upstream_signals(signal_name)
        # Combination of direct and transitive dependency
        direct_factor = min(fanin / 5.0, 1.0)
        transitive_factor = min(len(upstream) / self.total_signals, 1.0)
        return round(0.6 * direct_factor + 0.4 * transitive_factor, 4)

    # ─── Metric 4: Execution Probability ───────────────────────────────────
    def execution_probability(self, op: Operation) -> float:
        """
        Probability this operation executes on any given clock cycle.
        Based on opcode/condition coverage.
        """
        # Count total unique case items for same condition
        if op.condition:
            same_condition_ops = [
                o for o in self.rtl.operations
                if o.condition == op.condition and o.opcode_value is not None
            ]
            if same_condition_ops:
                n = len(same_condition_ops)
                if op.opcode_value == 'default':
                    return round(1.0 / (n + 1), 4)
                return round(1.0 / n, 4)

        # Unconditional assignments have high probability
        if not op.condition and not op.opcode_value:
            return 0.9

        return 0.5

    # ─── Metric 5: Structural Complexity ───────────────────────────────────
    def structural_complexity(self, op: Operation) -> float:
        """
        How complex is this operation's logic.
        Based on operator type and operand count.
        """
        op_complexity = OPERATOR_COMPLEXITY.get(op.operator, 0.5)
        # More operands = more complex
        operand_factor = min(len(op.rhs_signals) / 4.0, 1.0)
        return round(0.65 * op_complexity + 0.35 * operand_factor, 4)

    # ─── Compute all metrics for all operations ────────────────────────────
    def compute_all(self) -> List[Dict]:
        results = []
        for op in self.rtl.operations:
            sig = self.rtl.signals.get(op.lhs, Signal(
                name=op.lhs, signal_type='unknown', width=1
            ))
            iw  = self.initial_weight(sig)
            imp = self.impact_score(op.lhs)
            sus = self.susceptibility(op.lhs)
            ep  = self.execution_probability(op)
            sc  = self.structural_complexity(op)

            results.append({
                'line': op.line_number,
                'raw_line': op.raw_line,
                'signal': op.lhs,
                'operator': op.operator,
                'rhs_signals': op.rhs_signals,
                'condition': op.condition,
                'opcode_value': op.opcode_value,
                'initial_weight': iw,
                'impact_score': imp,
                'susceptibility': sus,
                'execution_probability': ep,
                'structural_complexity': sc
            })
        return results