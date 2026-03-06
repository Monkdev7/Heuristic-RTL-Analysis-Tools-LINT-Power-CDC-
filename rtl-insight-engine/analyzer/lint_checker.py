"""
Lint Rule Checker — 15 RTL lint rules.
Detects bad coding practices in Verilog.
"""

import re
from typing import List, Dict
from .parser import ParsedRTL

class LintChecker:

    def __init__(self, rtl: ParsedRTL, raw_content: str):
        self.rtl = rtl
        self.content = raw_content
        self.lines = raw_content.splitlines()
        self.violations = []

    def run_all(self) -> List[Dict]:
        self._check_uninitialized_regs()
        self._check_missing_default_in_case()
        self._check_blocking_in_sequential()
        self._check_sensitivity_list()
        self._check_implicit_net()
        self._check_magic_numbers()
        self._check_wide_mux()
        self._check_combinational_loop()
        self._check_unused_outputs()
        self._check_missing_reset()
        self._check_async_reset_release()
        self._check_clock_gating()
        self._check_multi_driven()
        self._check_latch_inference()
        self._check_truncation()
        self._check_initial_block()
        self._check_forever_loop()
        self._check_system_tasks()
        self._check_delays()
        self._check_timescale()
        return self.violations

    def _add(self, rule_id, severity, line_no, line, message, fix):
        self.violations.append({
            'rule_id': rule_id,
            'severity': severity,
            'line': line_no,
            'raw_line': line.strip(),
            'message': message,
            'fix': fix
        })

    def _check_uninitialized_regs(self):
        """LINT001: Reg used without reset assignment."""
        regs = [n for n, s in self.rtl.signals.items()
                if 'reg' in s.signal_type]
        reset_assigned = set()
        in_reset = False
        for i, line in enumerate(self.lines, 1):
            if 'if (rst)' in line or 'if (reset)' in line or 'if (rst_n)' in line:
                in_reset = True
            if in_reset and '<=' in line:
                m = re.match(r'\s*(\w+)\s*<=', line)
                if m:
                    reset_assigned.add(m.group(1))
            if in_reset and ('end' in line or 'else' in line):
                in_reset = False
        for reg in regs:
            if reg not in reset_assigned and reg not in self.rtl.clock_signals:
                self._add('LINT001', '🔴 Error', 0, f'reg {reg}',
                          f"Register '{reg}' has no reset assignment",
                          f"Add: if(rst) {reg} <= 0; in reset block")

    def _check_missing_default_in_case(self):
        """LINT002: Case statement missing default branch."""
        in_case = False
        has_default = False
        case_line = 0
        case_signal = ''
        for i, line in enumerate(self.lines, 1):
            m = re.match(r'\s*case\s*\((\w+)\)', line)
            if m:
                in_case = True
                has_default = False
                case_line = i
                case_signal = m.group(1)
            if in_case and 'default' in line:
                has_default = True
            if in_case and 'endcase' in line:
                if not has_default:
                    self._add('LINT002', '🟠 Warning', case_line,
                              line, f"case({case_signal}) missing default branch",
                              "Add: default: result <= 0; before endcase")
                in_case = False

    def _check_blocking_in_sequential(self):
        """LINT003: Blocking assignment (=) used inside always @posedge."""
        in_sequential = False
        for i, line in enumerate(self.lines, 1):
            if 'always' in line and ('posedge' in line or 'negedge' in line):
                in_sequential = True
            if in_sequential and 'end' in line and 'always' not in line:
                in_sequential = False
            if in_sequential:
                m = re.match(r'\s*(\w+)\s*=\s*(?!=)', line)
                if m and '//' not in line.split('=')[0]:
                    self._add('LINT003', '🔴 Error', i, line,
                              f"Blocking assignment '=' in sequential block for '{m.group(1)}'",
                              f"Change '=' to '<=' for '{m.group(1)}'")

    def _check_sensitivity_list(self):
        """LINT004: Incomplete sensitivity list in combinational always."""
        for i, line in enumerate(self.lines, 1):
            if 'always @(' in line and 'posedge' not in line and 'negedge' not in line:
                if '*' not in line:
                    self._add('LINT004', '🟠 Warning', i, line,
                              "Incomplete sensitivity list — use always @(*)",
                              "Replace with: always @(*) for combinational logic")

    def _check_implicit_net(self):
        """LINT005: Signal used but never declared."""
        declared = set(self.rtl.signals.keys())
        for op in self.rtl.operations:
            for sig in op.rhs_signals:
                if (sig not in declared
                        and not sig.isdigit()
                        and len(sig) > 1
                        and sig not in {'b0', 'b1', 'hFF', 'hFFFF'}):
                    self._add('LINT005', '🟡 Info', op.line_number, op.raw_line,
                              f"Signal '{sig}' used but not explicitly declared",
                              f"Add: wire {sig}; or input {sig}; declaration")

    def _check_magic_numbers(self):
        """LINT006: Hardcoded numeric literals (magic numbers)."""
        for i, line in enumerate(self.lines, 1):
            m = re.search(r"(?<!')\b([2-9]\d{2,})\b", line)
            if m and '//' not in line[:m.start()]:
                self._add('LINT006', '🟡 Info', i, line,
                          f"Magic number '{m.group(1)}' detected — use named parameter/localparam",
                          "Add: localparam MY_CONST = <value>; and use that name")

    def _check_wide_mux(self):
        """LINT007: Very wide case statement (>8 branches) — timing risk."""
        case_count = 0
        case_line = 0
        case_sig = ''
        for i, line in enumerate(self.lines, 1):
            m = re.match(r'\s*case\s*\((\w+)\)', line)
            if m:
                case_count = 0
                case_line = i
                case_sig = m.group(1)
            if re.match(r"\s*[\d']+\s*:", line):
                case_count += 1
            if 'endcase' in line and case_count > 8:
                self._add('LINT007', '🟠 Warning', case_line, f'case({case_sig})',
                          f"Wide MUX: {case_count} branches — may cause timing violations",
                          "Consider splitting into sub-cases or using priority encoder")

    def _check_combinational_loop(self):
        """LINT008: Signal drives itself (combinational loop)."""
        for op in self.rtl.operations:
            if op.lhs in op.rhs_signals:
                self._add('LINT008', '🔴 Error', op.line_number, op.raw_line,
                          f"Combinational loop: '{op.lhs}' drives itself",
                          f"Remove self-reference of '{op.lhs}' from RHS")

    def _check_unused_outputs(self):
        """LINT009: Output declared but never assigned."""
        outputs = {n for n, s in self.rtl.signals.items() if 'output' in s.signal_type}
        assigned = {op.lhs for op in self.rtl.operations}
        for out in outputs:
            if out not in assigned:
                self._add('LINT009', '🟠 Warning', 0, f'output {out}',
                          f"Output '{out}' declared but never assigned",
                          f"Add assignment for '{out}' or remove if unused")

    def _check_missing_reset(self):
        """LINT010: Sequential always block without reset."""
        for i, line in enumerate(self.lines, 1):
            if 'always' in line and 'posedge' in line:
                block_text = '\n'.join(self.lines[i:min(i+20, len(self.lines))])
                if 'rst' not in block_text and 'reset' not in block_text:
                    self._add('LINT010', '🟠 Warning', i, line,
                              "Sequential always block has no reset condition",
                              "Add: if(rst) begin ... end for safe initialization")

    def _check_async_reset_release(self):
        """LINT011: Async reset without sync release."""
        for i, line in enumerate(self.lines, 1):
            if 'negedge rst' in line or 'posedge rst' in line:
                self._add('LINT011', '🟡 Info', i, line,
                          "Asynchronous reset detected — ensure synchronous release",
                          "Use 2-stage sync release circuit for safe deassertion")

    def _check_clock_gating(self):
        """LINT012: Clock used in non-edge context (gating risk)."""
        for i, line in enumerate(self.lines, 1):
            for clk in self.rtl.clock_signals:
                if clk in line and 'posedge' not in line and 'negedge' not in line:
                    if '<=' in line or '=' in line:
                        self._add('LINT012', '🟡 Info', i, line,
                                  f"Clock signal '{clk}' used in data path — possible gating",
                                  "Never use clock signal as data; use dedicated clock enable")
                        break

    def _check_multi_driven(self):
        """LINT013: Signal assigned in multiple always blocks."""
        from collections import Counter
        lhs_list = [op.lhs for op in self.rtl.operations]
        counts = Counter(lhs_list)
        reported = set()
        for op in self.rtl.operations:
            if counts[op.lhs] > 4 and op.lhs not in reported:
                self._add('LINT013', '🟠 Warning', op.line_number, op.raw_line,
                          f"'{op.lhs}' assigned {counts[op.lhs]} times — possible multi-driver",
                          f"Ensure '{op.lhs}' is driven from single always block")
                reported.add(op.lhs)

    def _check_latch_inference(self):
        """LINT014: Incomplete if-else in combinational — latch inference."""
        for i, line in enumerate(self.lines, 1):
            if 'always @(*)' in line or "always @( * )" in line:
                block = '\n'.join(self.lines[i:min(i+15, len(self.lines))])
                if 'if' in block and 'else' not in block:
                    self._add('LINT014', '🔴 Error', i, line,
                              "Incomplete if without else in combinational block — latch inferred",
                              "Add else branch or use default assignment before if statement")

    def _check_truncation(self):
        """LINT015: Width mismatch — narrow signal on LHS of wide expression."""
        for op in self.rtl.operations:
            sig = self.rtl.signals.get(op.lhs)
            rhs_sigs_objs = [self.rtl.signals.get(s) for s in op.rhs_signals
                             if self.rtl.signals.get(s)]
            if sig and rhs_sigs_objs:
                max_rhs_width = max((s.width for s in rhs_sigs_objs), default=1)
                if sig.width < max_rhs_width and op.operator in ['ADD','MUL','SUB']:
                    self._add('LINT015', '🟠 Warning', op.line_number, op.raw_line,
                              f"Width truncation: '{op.lhs}'({sig.width}b) = {op.operator} of {max_rhs_width}b signals",
                              f"Widen '{op.lhs}' to {max_rhs_width+1} bits to avoid overflow truncation")

    def _check_initial_block(self):
        """LINT016: initial block — not synthesizable in most tools."""
        for i, line in enumerate(self.lines, 1):
            if re.match(r'\s*initial\b', line):
                self._add('LINT016', '🟠 Warning', i, line,
                          "initial block detected — not synthesizable in most tools",
                          "Replace with reset logic in always @(posedge clk) block")

    def _check_forever_loop(self):
        """LINT017: forever loop — simulation only, not synthesizable."""
        for i, line in enumerate(self.lines, 1):
            if re.search(r'\bforever\b', line) and '//' not in line.split('forever')[0]:
                self._add('LINT017', '🔴 Error', i, line,
                          "forever loop detected — simulation only, not synthesizable",
                          "Replace with synchronous always @(posedge clk) block")

    def _check_system_tasks(self):
        """LINT018: $display/$monitor system tasks — remove before synthesis."""
        sim_tasks = re.compile(r'\$(display|monitor|strobe|dumpvars|dumpfile|finish|stop)\b')
        for i, line in enumerate(self.lines, 1):
            m = sim_tasks.search(line)
            if m and '//' not in line[:m.start()]:
                self._add('LINT018', '🟡 Info', i, line,
                          f"Simulation task ${m.group(1)} found — remove before synthesis",
                          f"Remove ${m.group(1)} or wrap in `ifdef SIMULATION guard")

    def _check_delays(self):
        """LINT019: Timing delay #N — ignored by synthesis tools."""
        for i, line in enumerate(self.lines, 1):
            code = line[:line.index('//')] if '//' in line else line
            if re.search(r'#\s*\d+', code):
                self._add('LINT019', '🟠 Warning', i, line,
                          "Timing delay #N found — ignored by synthesis tools",
                          "Remove delay annotations; use synchronous design patterns")

    def _check_timescale(self):
        """LINT020: Missing `timescale directive."""
        if self.lines and not any('`timescale' in ln for ln in self.lines):
            self._add('LINT020', '🟡 Info', 1, self.lines[0],
                      "No `timescale directive found in file",
                      "Add: `timescale 1ns/1ps at the top of the file")