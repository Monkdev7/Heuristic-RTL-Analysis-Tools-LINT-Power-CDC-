"""
Risk Scoring Engine — computes 4 risk types per operation.
Also computes the overall RTL Health Score.
"""

from typing import List, Dict
from .parser import ParsedRTL

RISK_WEIGHTS = {
    'destructive':   {'impact': 0.6, 'complexity': 0.4},
    'intermittent':  {'exec_inv': 0.6, 'complexity': 0.4},
    'cdc':           {'fanout': 0.5, 'susceptibility': 0.5},
    'power':         {'exec_prob': 0.5, 'fanout': 0.5},
}

class RiskScorer:

    def __init__(self, rtl: ParsedRTL, graph):
        self.rtl = rtl
        self.graph = graph

    def _get_fanout_norm(self, signal: str) -> float:
        """Normalized fanout for a signal."""
        fo = self.graph.get_fanout(signal)
        return min(fo / 5.0, 1.0)

    def score(self, records: List[Dict]) -> List[Dict]:
        """Add risk scores to each record."""
        for r in records:
            sig = r['signal']
            fanout_norm = self._get_fanout_norm(sig)

            # 1. Destructive Risk
            r['destructive_risk'] = round(
                RISK_WEIGHTS['destructive']['impact'] * r['impact_score'] +
                RISK_WEIGHTS['destructive']['complexity'] * r['structural_complexity'],
                4
            )

            # 2. Intermittent Risk
            r['intermittent_risk'] = round(
                RISK_WEIGHTS['intermittent']['exec_inv'] * (1 - r['execution_probability']) +
                RISK_WEIGHTS['intermittent']['complexity'] * r['structural_complexity'],
                4
            )

            # 3. CDC Risk
            is_cross_domain = self._check_cdc(r)
            r['cdc_risk'] = round(
                (RISK_WEIGHTS['cdc']['fanout'] * fanout_norm +
                 RISK_WEIGHTS['cdc']['susceptibility'] * r['susceptibility']) *
                (1.5 if is_cross_domain else 0.4),
                4
            )
            r['has_cdc_issue'] = is_cross_domain

            # 4. Power Risk
            r['power_risk'] = round(
                RISK_WEIGHTS['power']['exec_prob'] * r['execution_probability'] +
                RISK_WEIGHTS['power']['fanout'] * fanout_norm,
                4
            )

            # Overall line risk (max of all risks)
            r['overall_risk'] = round(
                max(r['destructive_risk'], r['intermittent_risk'],
                    r['cdc_risk'], r['power_risk']),
                4
            )

            # Risk level label
            r['risk_level'] = self._risk_label(r['overall_risk'])

            # Fix suggestion
            r['fix_suggestion'] = self._suggest_fix(r)

        return records

    def _check_cdc(self, record: Dict) -> bool:
        """
        CDC detection: flag signals that genuinely cross clock domains.
        Uses name-based hints and clock-domain analysis from always blocks.
        """
        sig = record['signal']

        # Explicit CDC markers in signal name
        cdc_hints = ['fast', 'slow', 'async', 'domain', 'sync_in', 'sync_out',
                     'cross', 'xclk', 'cdc', 'meta']
        if any(h in sig.lower() for h in cdc_hints):
            return True

        # Only flag when MULTIPLE distinct clocks appear in always blocks
        clk_set = {ab['clock'] for ab in self.rtl.always_blocks if ab.get('clock')}
        if len(clk_set) > 1:
            # Conservative: flag only outputs that bridge between domains
            sig_obj = self.rtl.signals.get(sig)
            if sig_obj and 'output' in sig_obj.signal_type:
                return True
        return False

    def _risk_label(self, score: float) -> str:
        if score >= 0.75:
            return '🔴 Critical'
        elif score >= 0.5:
            return '🟠 High'
        elif score >= 0.3:
            return '🟡 Medium'
        else:
            return '🟢 Low'

    def _suggest_fix(self, record: Dict) -> str:
        fixes = []
        if record['cdc_risk'] > 0.5 and record['has_cdc_issue']:
            fixes.append("⚡ Add 2-flop synchronizer for CDC crossing")
        if record['power_risk'] > 0.6:
            fixes.append("🔋 Consider clock gating to reduce toggle activity")
        if record['destructive_risk'] > 0.6:
            fixes.append("🛡️ Add input validation / assertion for downstream protection")
        if record['intermittent_risk'] > 0.6:
            fixes.append("🔍 Add coverage point — this path is rarely executed")
        if record['structural_complexity'] > 0.7:
            fixes.append("🧩 Refactor: split complex combinational logic")
        if not fixes:
            fixes.append("✅ No critical issues detected")
        return " | ".join(fixes)

    def compute_health_score(self, records: List[Dict]) -> Dict:
        """
        RTL Health Score: 0–100.
        Lower risk = higher health.
        """
        if not records:
            return {'score': 100, 'grade': '🟢 Excellent', 'color': 'green'}

        avg_risk = sum(r['overall_risk'] for r in records) / len(records)
        health = round((1 - avg_risk) * 100)

        critical = sum(1 for r in records if r['risk_level'] == '🔴 Critical')
        high = sum(1 for r in records if r['risk_level'] == '🟠 High')

        # Deductions
        health -= critical * 5
        health -= high * 2
        health = max(0, min(100, health))

        if health >= 80:
            grade, color = '🟢 Excellent', 'green'
        elif health >= 60:
            grade, color = '🟡 Moderate', 'orange'
        elif health >= 40:
            grade, color = '🟠 Concerning', 'darkorange'
        else:
            grade, color = '🔴 High Risk', 'red'

        return {
            'score': health,
            'grade': grade,
            'color': color,
            'critical_count': critical,
            'high_count': high,
            'avg_risk': round(avg_risk, 4)
        }