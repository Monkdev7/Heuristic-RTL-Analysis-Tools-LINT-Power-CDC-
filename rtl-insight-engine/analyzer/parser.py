"""
RTL Parser — extracts signals, operators, conditions from Verilog
Uses pyverilog for AST parsing with regex fallback.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os

@dataclass
class Signal:
    name: str
    signal_type: str      # 'input', 'output', 'reg', 'wire', 'output reg'
    width: int = 1
    clock_domain: Optional[str] = None

@dataclass
class Operation:
    line_number: int
    raw_line: str
    operator: str
    lhs: str
    rhs_signals: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    opcode_value: Optional[str] = None

@dataclass
class ParsedRTL:
    module_name: str
    signals: Dict[str, Signal]
    operations: List[Operation]
    clock_signals: List[str]
    reset_signals: List[str]
    always_blocks: List[dict]

class RTLParser:

    OPERATORS = {
        '+': 'ADD', '-': 'SUB', '&': 'AND', '|': 'OR',
        '^': 'XOR', '>>': 'SHIFT_RIGHT', '<<': 'SHIFT_LEFT',
        '==': 'COMPARE', '!=': 'COMPARE', '?': 'TERNARY',
        '*': 'MUL', '/': 'DIV'
    }

    def __init__(self):
        self.signals: Dict[str, Signal] = {}
        self.operations: List[Operation] = []
        self.clock_signals: List[str] = []
        self.reset_signals: List[str] = []
        self.always_blocks: List[dict] = []
        self.module_name: str = "unknown"

    def parse(self, filepath: str) -> ParsedRTL:
        with open(filepath, 'r') as f:
            content = f.read()
        lines = content.splitlines()
        self._extract_module_name(content)
        self._extract_signals(content)
        self._extract_always_blocks(content)
        self._extract_operations(lines)
        self._detect_clock_reset()
        return ParsedRTL(
            module_name=self.module_name,
            signals=self.signals,
            operations=self.operations,
            clock_signals=self.clock_signals,
            reset_signals=self.reset_signals,
            always_blocks=self.always_blocks
        )

    def _extract_module_name(self, content: str):
        m = re.search(r'module\s+(\w+)', content)
        if m:
            self.module_name = m.group(1)

    def _extract_signals(self, content: str):
        # Match: input/output [reg] [width] name
        patterns = [
            (r'\b(input)\s+(?:wire\s+)?\[(\d+):(\d+)\]\s+(\w+)', 'input'),
            (r'\b(output)\s+reg\s+\[(\d+):(\d+)\]\s+(\w+)', 'output reg'),
            (r'\b(output)\s+\[(\d+):(\d+)\]\s+(\w+)', 'output'),
            (r'\b(input)\s+(\w+)\s*[,;)]', 'input_simple'),
            (r'\b(output)\s+reg\s+(\w+)\s*[,;)]', 'output_reg_simple'),
            (r'\b(output)\s+(\w+)\s*[,;)]', 'output_simple'),
            (r'\b(reg)\s+\[(\d+):(\d+)\]\s+(\w+)', 'reg'),
            (r'\b(wire)\s+\[(\d+):(\d+)\]\s+(\w+)', 'wire'),
            # SystemVerilog logic type
            (r'\b(input)\s+logic\s+\[(\d+):(\d+)\]\s+(\w+)', 'input'),
            (r'\b(output)\s+logic\s+\[(\d+):(\d+)\]\s+(\w+)', 'output'),
            (r'\b(logic)\s+\[(\d+):(\d+)\]\s+(\w+)', 'wire'),
            (r'\b(input)\s+logic\s+(\w+)\s*[,;)]', 'input_simple'),
            (r'\b(output)\s+logic\s+(\w+)\s*[,;)]', 'output_simple'),
        ]

        for pattern, sig_type in patterns:
            for m in re.finditer(pattern, content):
                groups = m.groups()
                if len(groups) == 4:
                    hi, lo = int(groups[1]), int(groups[2])
                    width = hi - lo + 1
                    name = groups[3]
                    stype = sig_type
                elif len(groups) == 2:
                    name = groups[1]
                    width = 1
                    stype = sig_type.replace('_simple', '').replace('_reg', ' reg')
                else:
                    continue
                if name and name not in ['begin', 'end', 'if', 'else', 'case']:
                    self.signals[name] = Signal(
                        name=name,
                        signal_type=stype,
                        width=width
                    )

        # Also pick up simple 1-bit inputs
        for m in re.finditer(r'\b(input|output)\s+(\w+)\b', content):
            name = m.group(2)
            if name not in self.signals and name not in ['wire', 'reg', 'logic']:
                self.signals[name] = Signal(
                    name=name,
                    signal_type=m.group(1),
                    width=1
                )

    def _extract_always_blocks(self, content: str):
        for m in re.finditer(r'always\s*@\s*\(([^)]+)\)', content):
            sensitivity = m.group(1)
            block = {
                'sensitivity': sensitivity,
                'is_clocked': 'posedge' in sensitivity or 'negedge' in sensitivity,
                'clock': None,
                'reset': None
            }
            clk_m = re.search(r'(?:posedge|negedge)\s+(\w+)', sensitivity)
            if clk_m:
                block['clock'] = clk_m.group(1)
            self.always_blocks.append(block)

    def _extract_operations(self, lines: List[str]):
        case_condition = None
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track case statements
            case_m = re.match(r'case\s*\((\w+)\)', stripped)
            if case_m:
                case_condition = case_m.group(1)

            if stripped in ['endcase', 'end']:
                case_condition = None

            # Case items like: 3'b000: result <= a + b;
            case_item_m = re.match(r"([\d'bho]+|default)\s*:\s*(\w+)\s*<=\s*(.+?);", stripped)
            if case_item_m:
                opcode_val = case_item_m.group(1)
                lhs = case_item_m.group(2)
                rhs = case_item_m.group(3).strip()
                op = self._detect_operator(rhs)
                rhs_sigs = self._extract_rhs_signals(rhs)
                self.operations.append(Operation(
                    line_number=i,
                    raw_line=stripped,
                    operator=op,
                    lhs=lhs,
                    rhs_signals=rhs_sigs,
                    condition=case_condition,
                    opcode_value=opcode_val
                ))
                continue

            # Non-blocking assignment: result <= expr;
            assign_m = re.match(r'(\w+)\s*<=\s*(.+?);', stripped)
            if assign_m:
                lhs = assign_m.group(1)
                rhs = assign_m.group(2).strip()
                op = self._detect_operator(rhs)
                rhs_sigs = self._extract_rhs_signals(rhs)
                self.operations.append(Operation(
                    line_number=i,
                    raw_line=stripped,
                    operator=op,
                    lhs=lhs,
                    rhs_signals=rhs_sigs
                ))
                continue

            # Continuous assignment: assign x = expr;
            cont_m = re.match(r'assign\s+(\w+)\s*=\s*(.+?);', stripped)
            if cont_m:
                lhs = cont_m.group(1)
                rhs = cont_m.group(2).strip()
                op = self._detect_operator(rhs)
                rhs_sigs = self._extract_rhs_signals(rhs)
                self.operations.append(Operation(
                    line_number=i,
                    raw_line=stripped,
                    operator=op,
                    lhs=lhs,
                    rhs_signals=rhs_sigs
                ))

    def _detect_operator(self, expr: str) -> str:
        for op_sym in ['>>', '<<', '+', '-', '&', '|', '^', '*', '/', '==', '!=', '?']:
            if op_sym in expr:
                return self.OPERATORS.get(op_sym, op_sym)
        return 'ASSIGN'

    def _extract_rhs_signals(self, expr: str) -> List[str]:
        tokens = re.findall(r'\b([a-zA-Z_]\w*)\b', expr)
        reserved = {'begin','end','if','else','case','endcase','posedge',
                    'negedge','always','module','endmodule','assign','reg',
                    'wire','input','output','default'}
        return [t for t in tokens if t not in reserved and not t.isdigit()]

    def _detect_clock_reset(self):
        clk_patterns = ['clk', 'clock', 'sys_clk', 'fast_clk', 'slow_clk']
        rst_patterns = ['rst', 'reset', 'rst_n', 'reset_n', 'arst']

        for name in self.signals:
            nl = name.lower()
            if any(p in nl for p in clk_patterns):
                self.clock_signals.append(name)
            if any(p in nl for p in rst_patterns):
                self.reset_signals.append(name)