from .parser import RTLParser
from .pdf_report import generate_pdf_report
from .ast_builder import DependencyGraph
from .metrics import MetricsEngine
from .normalizer import normalize
from .risk_scorer import RiskScorer
from .lint_checker import LintChecker
from .waveform import WaveformSimulator

def analyze_rtl(filepath: str):
    """Full pipeline: parse → graph → metrics → normalize → risk score → lint → waveform."""
    # Read raw content for lint checker
    with open(filepath, 'r') as f:
        raw_content = f.read()

    parser = RTLParser()
    rtl = parser.parse(filepath)

    graph = DependencyGraph(rtl)
    engine = MetricsEngine(rtl, graph)

    records = engine.compute_all()
    records = normalize(records)

    scorer = RiskScorer(rtl, graph)
    records = scorer.score(records)
    health = scorer.compute_health_score(records)

    # Lint check
    lint = LintChecker(rtl, raw_content)
    lint_violations = lint.run_all()

    # Waveform simulation
    sim = WaveformSimulator(records)
    waveforms = sim.simulate()
    toggles = sim.compute_toggle_count(waveforms)

    return rtl, graph, records, health, lint_violations, waveforms, toggles