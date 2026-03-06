"""
PDF Report Generator — creates professional RTL analysis report.
Fixed: strips all unicode/emoji characters incompatible with Helvetica.
"""

from fpdf import FPDF
import re
from typing import List, Dict
from datetime import datetime


def clean(text: str) -> str:
    """Remove all non-ASCII and emoji characters for PDF compatibility."""
    text = str(text)
    # Remove emoji and special unicode chars
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    # Remove any remaining non-printable chars
    text = re.sub(r'[^\x20-\x7E]', '', text)
    return text.strip()


def clean_risk(risk: str) -> str:
    """Convert risk label emoji to plain text."""
    risk = str(risk)
    mapping = {
        '🔴 Critical': 'CRITICAL',
        '🟠 High':     'HIGH',
        '🟡 Medium':   'MEDIUM',
        '🟢 Low':      'LOW',
    }
    for k, v in mapping.items():
        if k in risk:
            return v
    return clean(risk)


def clean_severity(sev: str) -> str:
    """Convert severity emoji to plain text."""
    sev = str(sev)
    if 'Error'   in sev: return 'ERROR'
    if 'Warning' in sev: return 'WARNING'
    if 'Info'    in sev: return 'INFO'
    return clean(sev)


class RTLReportPDF(FPDF):

    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_fill_color(30, 30, 60)
        self.set_text_color(255, 255, 255)
        self.cell(0, 14, '  RTL Insight Engine -- Analysis Report',
                  fill=True, ln=True)
        self.set_text_color(120, 120, 120)
        self.set_font('Helvetica', '', 9)
        self.cell(0, 6,
                  f'  Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                  ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f'RTL Insight Engine  |  Page {self.page_no()}',
                  align='C')

    def section_title(self, title: str):
        self.ln(4)
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(102, 126, 234)
        self.set_text_color(255, 255, 255)
        self.cell(0, 9, f'  {clean(title)}', fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def health_banner(self, health: Dict):
        score = health['score']
        grade = clean(health.get('grade', ''))

        if score >= 80:
            r, g, b = 34, 197, 94
        elif score >= 60:
            r, g, b = 234, 179, 8
        elif score >= 40:
            r, g, b = 249, 115, 22
        else:
            r, g, b = 239, 68, 68

        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 28)
        self.cell(60, 20, f'  {score} / 100', fill=True, ln=False)

        self.set_font('Helvetica', 'B', 14)
        self.set_fill_color(50, 50, 80)
        self.cell(0, 20, f'   {grade}', fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def summary_row(self, label: str, value: str, color=None):
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(240, 240, 250)
        self.cell(70, 7, f'  {clean(label)}', fill=True, border=1)
        self.set_font('Helvetica', '', 10)
        if color:
            self.set_text_color(*color)
        self.set_fill_color(255, 255, 255)
        self.cell(0, 7, f'  {clean(value)}', fill=True, border=1, ln=True)
        self.set_text_color(0, 0, 0)

    def risk_table(self, records: List[Dict]):
        headers = ['Line', 'Signal', 'Operator', 'Risk Level',
                   'Overall', 'Destructive', 'Intermittent']
        widths  = [14, 28, 22, 28, 20, 24, 24]

        # Header
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(30, 30, 60)
        self.set_text_color(255, 255, 255)
        for h, w in zip(headers, widths):
            self.cell(w, 7, h, fill=True, border=1)
        self.ln()
        self.set_text_color(0, 0, 0)

        # Rows
        self.set_font('Helvetica', '', 7)
        sorted_rec = sorted(records, key=lambda x: x['overall_risk'],
                            reverse=True)[:20]

        for r in sorted_rec:
            risk = r.get('risk_level', '')
            if 'Critical' in risk:
                self.set_fill_color(254, 226, 226)
            elif 'High' in risk:
                self.set_fill_color(255, 237, 213)
            elif 'Medium' in risk:
                self.set_fill_color(254, 249, 195)
            else:
                self.set_fill_color(220, 252, 231)

            row = [
                str(r.get('line', '')),
                clean(r.get('signal', ''))[:14],
                clean(r.get('operator', '')),
                clean_risk(risk),
                f"{r.get('overall_risk', 0):.3f}",
                f"{r.get('destructive_risk', 0):.3f}",
                f"{r.get('intermittent_risk', 0):.3f}",
            ]
            for val, w in zip(row, widths):
                self.cell(w, 6, str(val), fill=True, border=1)
            self.ln()

    def lint_table(self, violations: List[Dict]):
        if not violations:
            self.set_font('Helvetica', 'I', 10)
            self.set_text_color(34, 197, 94)
            self.cell(0, 8, '  No lint violations found.', ln=True)
            self.set_text_color(0, 0, 0)
            return

        headers = ['Rule ID', 'Severity', 'Line', 'Message']
        widths  = [20, 22, 12, 126]

        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(30, 30, 60)
        self.set_text_color(255, 255, 255)
        for h, w in zip(headers, widths):
            self.cell(w, 7, h, fill=True, border=1)
        self.ln()
        self.set_text_color(0, 0, 0)

        self.set_font('Helvetica', '', 7)
        for v in violations[:25]:
            sev = v.get('severity', '')
            if 'Error'   in sev: self.set_fill_color(254, 226, 226)
            elif 'Warning' in sev: self.set_fill_color(255, 237, 213)
            else:                  self.set_fill_color(254, 249, 195)

            row = [
                clean(v.get('rule_id', '')),
                clean_severity(sev),
                str(v.get('line', '')),
                clean(v.get('message', ''))[:65],
            ]
            for val, w in zip(row, widths):
                self.cell(w, 6, str(val), fill=True, border=1)
            self.ln()


def generate_pdf_report(
    module_name: str,
    health: Dict,
    records: List[Dict],
    lint_violations: List[Dict],
    rtl_signals: Dict,
    toggles: Dict
) -> bytes:
    """Generate full PDF report and return as bytes."""

    pdf = RTLReportPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    # ── Section 1: Health Summary ──────────────────────────────────────────
    pdf.section_title('1. RTL Health Summary')
    pdf.health_banner(health)
    pdf.summary_row('Module Name',      clean(module_name))
    pdf.summary_row('Total Signals',    str(len(rtl_signals)))
    pdf.summary_row('Total Operations', str(len(records)))
    pdf.summary_row('Critical Issues',  str(health.get('critical_count', 0)),
                    color=(200, 40, 40))
    pdf.summary_row('High Risk Issues', str(health.get('high_count', 0)),
                    color=(200, 100, 0))
    pdf.summary_row('Lint Violations',  str(len(lint_violations)))
    pdf.summary_row('Average Risk',     f"{health.get('avg_risk', 0):.4f}")

    # ── Section 2: Signal Inventory ────────────────────────────────────────
    pdf.section_title('2. Signal Inventory')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(30, 30, 60)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(['Signal Name', 'Type', 'Width (bits)', 'Toggles'],
                    [50, 40, 40, 40]):
        pdf.cell(w, 7, h, fill=True, border=1)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 8)

    for i, (name, sig) in enumerate(rtl_signals.items()):
        pdf.set_fill_color(248, 248, 255) if i % 2 == 0 \
            else pdf.set_fill_color(255, 255, 255)
        for val, w in zip(
            [clean(name), clean(sig.signal_type),
             str(sig.width), str(toggles.get(name, 0))],
            [50, 40, 40, 40]
        ):
            pdf.cell(w, 6, str(val), fill=True, border=1)
        pdf.ln()

    # ── Section 3: Risk Analysis ───────────────────────────────────────────
    pdf.section_title('3. Risk Analysis -- Top 20 Violations')
    pdf.risk_table(records)

    # ── Section 4: Lint Violations ─────────────────────────────────────────
    pdf.section_title('4. Lint Rule Violations')
    pdf.lint_table(lint_violations)

    # ── Section 5: Fix Recommendations ────────────────────────────────────
    pdf.section_title('5. Fix Recommendations')
    top5 = sorted(records, key=lambda x: x['overall_risk'],
                  reverse=True)[:5]

    for i, r in enumerate(top5, 1):
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(230, 230, 250)
        label = (f"  #{i} Line {r.get('line','')}: "
                 f"{clean(r.get('raw_line',''))[:50]} "
                 f"[{clean_risk(r.get('risk_level',''))}]")
        pdf.cell(0, 7, label, fill=True, ln=True)

        pdf.set_font('Helvetica', '', 8)
        fixes = r.get('fix_suggestion', '')
        for fix in fixes.split(' | '):
            fix_clean = clean(fix)
            if fix_clean:
                pdf.cell(8, 6, '', ln=False)
                pdf.cell(0, 6, f'-> {fix_clean}', ln=True)
        pdf.ln(1)

    return bytes(pdf.output())