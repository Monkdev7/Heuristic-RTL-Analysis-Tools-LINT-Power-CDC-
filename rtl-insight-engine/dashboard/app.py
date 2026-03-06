"""
RTL Health Analyzer — Professional Streamlit Dashboard
Run: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, sys, tempfile
import networkx as nx
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from analyzer import analyze_rtl

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RTL Health Analyzer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.navbar {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    border: 1px solid #1e40af;
    padding: 20px 28px;
    border-radius: 12px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.navbar-title { font-size:1.75rem; font-weight:700; color:#f8fafc; letter-spacing:-0.5px; }
.navbar-sub   { font-size:0.82rem; color:#94a3b8; margin-top:3px; }
.navbar-badge {
    background:#1d4ed8; color:#dbeafe;
    font-size:0.72rem; font-weight:600;
    padding:4px 14px; border-radius:999px; letter-spacing:0.4px;
}

.mcard {
    background:#0f172a; border:1px solid #1e293b;
    border-radius:12px; padding:20px 22px;
    position:relative; overflow:hidden; height:100%;
}
.mcard-accent {
    position:absolute; top:0; left:0; right:0;
    height:3px; border-radius:12px 12px 0 0;
}
.mcard-label  { font-size:0.7rem; font-weight:600; color:#64748b;
                text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; }
.mcard-value  { font-size:2rem; font-weight:700; color:#f1f5f9; line-height:1.1; }
.mcard-sub    { font-size:0.72rem; color:#475569; margin-top:5px; }

.sec-header {
    font-size:0.72rem; font-weight:600; color:#475569;
    text-transform:uppercase; letter-spacing:1px;
    padding-bottom:10px; border-bottom:1px solid #1e293b; margin-bottom:18px;
}

.fix-card {
    background:#0f172a; border:1px solid #1e293b;
    border-radius:10px; padding:16px 20px; margin-bottom:4px;
}
.fix-card-code {
    font-family:'JetBrains Mono','Fira Code',monospace; font-size:0.8rem;
    background:#1e293b; padding:7px 12px; border-radius:6px;
    color:#93c5fd; margin:8px 0; word-break:break-all;
}
.fix-item { font-size:0.81rem; color:#94a3b8; padding:3px 0; }

.rtl-viewer {
    background:#0a0f1e; border:1px solid #1e293b;
    border-radius:10px; padding:12px 0;
    max-height:560px; overflow-y:auto;
    font-family:'JetBrains Mono','Fira Code','Courier New',monospace;
    scrollbar-width:thin; scrollbar-color:#1e293b #0a0f1e;
}
.rtl-viewer::-webkit-scrollbar { width:6px; }
.rtl-viewer::-webkit-scrollbar-track { background:#0a0f1e; }
.rtl-viewer::-webkit-scrollbar-thumb { background:#1e293b; border-radius:3px; }
.rtl-row {
    display:flex; align-items:baseline; gap:0;
    padding:1px 0; border-left:3px solid transparent;
    transition:background 0.1s ease;
}
.rtl-row:hover { background:#1e293b55 !important; }
.rtl-num {
    color:#2d3f55; min-width:42px; text-align:right; padding:0 12px 0 10px;
    font-size:0.72rem; user-select:none; flex-shrink:0;
    border-right:1px solid #1a2535;
}
.rtl-code  { font-size:0.79rem; color:#94a3b8; flex:1; white-space:pre;
             padding:0 10px; overflow:hidden; }
.rtl-badge {
    font-size:0.6rem; font-weight:700; flex-shrink:0;
    padding:0 7px; border-radius:999px; margin-right:10px;
    white-space:nowrap; align-self:center; line-height:1.7;
}
.rtl-sig  { font-size:0.6rem; color:#64748b; flex-shrink:0;
             margin-right:8px; align-self:center; white-space:nowrap;
             max-width:120px; overflow:hidden; text-overflow:ellipsis; }
.rtl-crit { background:#350a0a33; border-left-color:#ef4444; }
.rtl-high { background:#33130633; border-left-color:#f97316; }
.rtl-med  { background:#321e0233; border-left-color:#eab308; }
.rtl-low  { background:#0f172a55; border-left-color:#475569; }
.rtl-kw      { color:#93c5fd; font-weight:600; }
.rtl-comment { color:#374151; font-style:italic; }
.rtl-string  { color:#fcd34d; }
.rtl-pp      { color:#e879f9; }
.rtl-numlit  { color:#86efac; }

div[data-testid="stMetric"] {
    background:#0f172a; border:1px solid #1e293b; border-radius:10px; padding:14px;
}
[data-testid="stFileUploader"] {
    border:1px solid #1e293b !important; border-radius:10px !important;
}
section[data-testid="stSidebar"] { background:#0d1424; border-right:1px solid #1e293b; }
</style>
""", unsafe_allow_html=True)

# ── Chart helpers ──────────────────────────────────────────────────────────────
CHART_BG   = "rgba(0,0,0,0)"
FONT_COLOR = "#94a3b8"
GRID_COLOR = "#1e293b"
RISK_COLORS = {
    "🔴 Critical": "#ef4444", "🟠 High": "#f97316",
    "🟡 Medium":   "#eab308", "🟢 Low":  "#22c55e",
}

def _chart(fig, title="", height=320):
    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color="#cbd5e1"), x=0),
        paper_bgcolor=CHART_BG, plot_bgcolor="#0d1424",
        font=dict(color=FONT_COLOR, size=11),
        margin=dict(l=16, r=16, t=38, b=16), height=height,
        xaxis=dict(gridcolor=GRID_COLOR, linecolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, linecolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    )
    return fig

# ── Cache ─────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _run_analysis(file_bytes: bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.v', mode='wb') as tmp:
        tmp.write(file_bytes); pth = tmp.name
    try:
        return analyze_rtl(pth)
    finally:
        try: os.unlink(pth)
        except Exception: pass


# ─────────────────────────────────────────────────────────────────────────────
# render_header
# ─────────────────────────────────────────────────────────────────────────────
def render_header(module_name=""):
    sub = (f"Analyzing module: <b>{module_name}</b>"
           if module_name else "Upload a Verilog / SystemVerilog file to begin")
    st.markdown(f"""
    <div class="navbar">
      <div>
        <div class="navbar-title">🔬 RTL Health Analyzer</div>
        <div class="navbar-sub">{sub}</div>
      </div>
      <div class="navbar-badge">v2.0 &nbsp;·&nbsp; Verilog / SystemVerilog</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# render_health_gauge
# ─────────────────────────────────────────────────────────────────────────────
def render_health_gauge(health, df):
    score = health["score"]
    grade = health["grade"].split(" ", 1)[-1]

    # Weighted risk score: destructive is heaviest, then intermittent, cdc, power
    weights = {"destructive_risk": 0.40, "intermittent_risk": 0.25,
               "cdc_risk": 0.20, "power_risk": 0.15}
    weighted = sum(
        df[col].mean() * w
        for col, w in weights.items()
        if col in df.columns
    )
    computed_score = max(0, min(100, round(100 - weighted * 100)))
    # Prefer the analyzer's own score if present, else use computed
    display_score = score if score else computed_score

    needle_color = (
        "#22c55e" if display_score >= 80 else
        ("#eab308" if display_score >= 60 else "#ef4444")
    )
    status_text = (
        "Healthy Design" if display_score >= 80 else
        ("Moderate Risk" if display_score >= 60 else "High Risk")
    )

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=display_score,
        number=dict(
            font=dict(size=52, color=needle_color, family="Inter"),
            suffix="",
        ),
        title=dict(
            text=f"RTL Health Score<br><span style='font-size:0.85em;color:#64748b'>{grade} — {status_text}</span>",
            font=dict(size=15, color="#cbd5e1", family="Inter"),
        ),
        gauge=dict(
            axis=dict(
                range=[0, 100],
                tickwidth=1,
                tickcolor="#334155",
                tickvals=[0, 20, 40, 60, 80, 100],
                ticktext=["0", "20", "40", "60", "80", "100"],
                tickfont=dict(size=11, color="#64748b"),
            ),
            bar=dict(color=needle_color, thickness=0.25),
            bgcolor="#0d1424",
            borderwidth=0,
            steps=[
                dict(range=[0,  60], color="#2d0a0a"),   # red zone
                dict(range=[60, 80], color="#2d2000"),   # yellow zone
                dict(range=[80, 100], color="#062816"),  # green zone
            ],
            threshold=dict(
                line=dict(color=needle_color, width=3),
                thickness=0.75,
                value=display_score,
            ),
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Inter"),
        margin=dict(l=30, r=30, t=20, b=10),
        height=240,
    )

    # Legend labels for the three zones
    zone_html = (
        '<div style="display:flex;justify-content:center;gap:28px;'
        'margin-top:-8px;margin-bottom:8px">'
        '<span style="font-size:0.71rem;font-weight:600;color:#ef4444">'
        '■ 0–60 High Risk</span>'
        '<span style="font-size:0.71rem;font-weight:600;color:#eab308">'
        '■ 60–80 Moderate</span>'
        '<span style="font-size:0.71rem;font-weight:600;color:#22c55e">'
        '■ 80–100 Healthy</span>'
        '</div>'
    )

    # Center the gauge using columns
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.plotly_chart(fig, use_container_width=True, key="health_gauge")
        st.markdown(zone_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# render_summary_cards
# ─────────────────────────────────────────────────────────────────────────────
def render_summary_cards(df, health, lint_violations, rtl):
    score    = health["score"]
    grade    = health["grade"].split(" ", 1)[-1]
    crit     = health.get("critical_count", 0)
    high     = health.get("high_count", 0)
    cdc_n    = int(df["has_cdc_issue"].sum()) if "has_cdc_issue" in df.columns else 0
    power_n  = int((df["power_risk"] > 0.5).sum()) if "power_risk" in df.columns else 0
    hc = "#22c55e" if score >= 80 else ("#eab308" if score >= 60 else ("#f97316" if score >= 40 else "#ef4444"))

    cards = [
        (hc,       str(score),              "Health Score",        grade),
        ("#ef4444", str(crit),              "Critical Ops",        f"{high} high-risk"),
        ("#f97316", str(len(lint_violations)),"Lint Violations",   "20-rule checker"),
        ("#a855f7", str(cdc_n),             "CDC Signals",         "Domain crossings"),
        ("#3b82f6", str(power_n),           "High Power Signals",  "Toggle > 0.5"),
        ("#06b6d4", str(len(rtl.signals)),  "Signals Parsed",      f"{len(rtl.clock_signals)} clk · {len(rtl.reset_signals)} rst"),
        ("#eab308", str(len(df)),           "Operations",          f"avg risk {health.get('avg_risk',0):.3f}"),
        ("#64748b", rtl.module_name,        "Module",              "Top-level entity"),
    ]

    st.markdown('<div class="sec-header">Overview</div>', unsafe_allow_html=True)
    row1 = st.columns(4)
    row2 = st.columns(4)
    rows = row1 + row2
    for col, (color, val, lbl, sub) in zip(rows, cards):
        with col:
            st.markdown(f"""
            <div class="mcard">
              <div class="mcard-accent" style="background:{color}"></div>
              <div class="mcard-label">{lbl}</div>
              <div class="mcard-value" style="color:{color}">{val}</div>
              <div class="mcard-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# render_risk_tables
# ─────────────────────────────────────────────────────────────────────────────
def _score_color(v):
    if v >= 0.75: return "background:#450a0a;color:#fca5a5"
    if v >= 0.5:  return "background:#431407;color:#fdba74"
    if v >= 0.3:  return "background:#422006;color:#fde68a"
    return "background:#052e16;color:#86efac"

def render_risk_tables(df):
    st.markdown('<div class="sec-header">Risk Rankings</div>', unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["💥 Destructive", "🎲 Intermittent", "⚡ CDC", "🔋 Power"])
    pairs = [
        (t1, "destructive_risk",  "Destructive",  "#ef4444"),
        (t2, "intermittent_risk", "Intermittent", "#f97316"),
        (t3, "cdc_risk",          "CDC",           "#a855f7"),
        (t4, "power_risk",        "Power",         "#3b82f6"),
    ]
    for tab, col, label, color in pairs:
        with tab:
            if col not in df.columns:
                st.info(f"No {label} data."); continue
            cols_show = [c for c in ["line","signal","operator","raw_line",col,"risk_level"] if c in df.columns]
            tbl = (df[cols_show].sort_values(col, ascending=False)
                                .head(20).reset_index(drop=True))
            tbl.index += 1; tbl.index.name = "Rank"

            rc1, rc2 = st.columns([3, 2])
            with rc1:
                st.dataframe(
                    tbl.style.map(_score_color, subset=[col])
                             .format({col: "{:.4f}"}),
                    use_container_width=True, height=360,
                )
            with rc2:
                fig = px.bar(
                    tbl.reset_index(), x="signal", y=col,
                    color=col,
                    color_continuous_scale=["#1e3a5f", color, "#ef4444"],
                    text=col,
                )
                fig.update_traces(texttemplate="%{text:.2f}", textposition="outside",
                                  marker_line_width=0)
                _chart(fig, f"Top {label} Risk by Signal", height=360)
                fig.update_layout(showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# render_charts
# ─────────────────────────────────────────────────────────────────────────────
def render_charts(df, toggles, waveform_cycles, waveforms):
    st.markdown('<div class="sec-header">Visualizations</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        top = df.sort_values("overall_risk", ascending=False).head(12).copy()
        top["label"] = top.apply(lambda r: f"L{r['line']} {r['signal']}", axis=1)
        fig = px.bar(top, x="overall_risk", y="label", orientation="h",
                     color="overall_risk",
                     color_continuous_scale=["#1e3a5f","#3b82f6","#ef4444"])
        fig.update_traces(marker_line_width=0)
        fig.update_layout(yaxis=dict(autorange="reversed"))
        _chart(fig, "Top 12 Riskiest Lines", 320)
        fig.update_layout(coloraxis_showscale=False,
                          xaxis_title="Risk Score", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        cnts = df["risk_level"].value_counts().reset_index()
        cnts.columns = ["Level","Count"]
        fig2 = px.pie(cnts, names="Level", values="Count",
                      color="Level", color_discrete_map=RISK_COLORS, hole=0.55)
        fig2.update_traces(textinfo="percent+label",
                           marker=dict(line=dict(color="#0d1424", width=2)))
        _chart(fig2, "Risk Level Distribution", 320)
        fig2.update_layout(showlegend=False, plot_bgcolor=CHART_BG)
        st.plotly_chart(fig2, use_container_width=True)

    with c3:
        fig3 = px.histogram(df, x="overall_risk", nbins=20,
                            color_discrete_sequence=["#3b82f6"])
        fig3.update_traces(marker_line_color="#1e293b", marker_line_width=1)
        _chart(fig3, "Risk Score Frequency", 320)
        fig3.update_layout(xaxis_title="Risk Score", yaxis_title="Count")
        st.plotly_chart(fig3, use_container_width=True)

    c4, c5 = st.columns(2)
    with c4:
        cats = ["Destructive","Intermittent","CDC","Power","Complexity"]
        vals = [df[k].mean() for k in ["destructive_risk","intermittent_risk",
                                        "cdc_risk","power_risk","structural_complexity"]]
        fig4 = go.Figure(go.Scatterpolar(
            r=vals+[vals[0]], theta=cats+[cats[0]],
            fill="toself",
            fillcolor="rgba(59,130,246,0.12)",
            line=dict(color="#3b82f6", width=2),
            marker=dict(color="#3b82f6", size=5),
        ))
        fig4.update_layout(
            polar=dict(
                bgcolor="#0d1424",
                radialaxis=dict(visible=True, range=[0,1], gridcolor=GRID_COLOR,
                                tickfont=dict(size=9,color="#475569"), linecolor=GRID_COLOR),
                angularaxis=dict(gridcolor=GRID_COLOR, linecolor=GRID_COLOR,
                                 tickfont=dict(color="#94a3b8")),
            ),
            paper_bgcolor=CHART_BG, font=dict(color=FONT_COLOR),
            margin=dict(l=30,r=30,t=50,b=30), height=320,
            title=dict(text="Risk Profile Radar", font=dict(size=12,color="#cbd5e1"),x=0),
        )
        st.plotly_chart(fig4, use_container_width=True)

    with c5:
        avg_df = pd.DataFrame({
            "Category": ["Destructive","Intermittent","CDC","Power"],
            "Score":    [df["destructive_risk"].mean(), df["intermittent_risk"].mean(),
                         df["cdc_risk"].mean(), df["power_risk"].mean()],
            "Color":    ["#ef4444","#f97316","#a855f7","#3b82f6"],
        })
        fig5 = px.bar(avg_df, x="Category", y="Score",
                      color="Category",
                      color_discrete_map={r["Category"]:r["Color"] for _,r in avg_df.iterrows()},
                      text="Score")
        fig5.update_traces(texttemplate="%{text:.3f}", textposition="outside",
                           marker_line_width=0)
        _chart(fig5, "Average Risk by Category", 320)
        fig5.update_layout(showlegend=False, yaxis=dict(range=[0,1.1]))
        st.plotly_chart(fig5, use_container_width=True)

    # Waveform row
    if toggles and waveforms:
        w1, w2 = st.columns([2,3])
        with w1:
            tdf = pd.DataFrame([
                {"Signal":s,"Toggles":t,
                 "Activity":"High" if t>10 else ("Medium" if t>5 else "Low")}
                for s,t in sorted(toggles.items(), key=lambda x:x[1], reverse=True)
            ])
            fw = px.bar(tdf, x="Toggles", y="Signal", orientation="h",
                        color="Activity",
                        color_discrete_map={"High":"#ef4444","Medium":"#f97316","Low":"#22c55e"})
            fw.update_traces(marker_line_width=0)
            fw.update_layout(yaxis=dict(autorange="reversed"))
            _chart(fw, f"Toggle Activity ({waveform_cycles} cycles)", 300)
            st.plotly_chart(fw, use_container_width=True)
        with w2:
            sigs = list(waveforms.keys())[:8]
            cyc  = list(range(waveform_cycles))
            fw2  = go.Figure()
            for i, sig in enumerate(sigs):
                wave = waveforms[sig][:waveform_cycles]
                fw2.add_trace(go.Scatter(
                    x=cyc, y=[v+i*2.2 for v in wave],
                    mode="lines", name=sig,
                    line=dict(width=1.8, shape="hv",
                              color=f"hsl({i*42},65%,58%)"),
                ))
            fw2.update_layout(
                title=dict(text="Digital Waveform Simulation",
                           font=dict(size=12,color="#cbd5e1"),x=0),
                xaxis_title="Clock Cycle",
                yaxis=dict(tickvals=[i*2.2+1 for i in range(len(sigs))],
                           ticktext=sigs, showgrid=False,
                           tickfont=dict(size=10,color="#94a3b8")),
                paper_bgcolor=CHART_BG, plot_bgcolor="#0a0f1e",
                font=dict(color=FONT_COLOR), showlegend=False,
                height=300, margin=dict(l=16,r=16,t=38,b=16),
            )
            st.plotly_chart(fw2, use_container_width=True)


import re as _re

_VL_KW = {
    'module','endmodule','input','output','inout','wire','reg','logic',
    'always','always_ff','always_comb','always_latch','assign','if','else',
    'begin','end','case','casex','casez','endcase','for','while','forever',
    'initial','parameter','localparam','posedge','negedge','or','and','not',
    'function','endfunction','task','endtask','generate','endgenerate',
    'integer','real','time','signed','unsigned','tri','supply0','supply1',
    'default','repeat','fork','join','disable','wait','buf',
}

def _hl(raw: str) -> str:
    """Return HTML-escaped, syntax-highlighted single Verilog line."""
    parts = []
    s = raw
    i = 0
    while i < len(s):
        # single-line comment
        if s[i:i+2] == '//':
            esc = s[i:].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            parts.append(f'<span class="rtl-comment">{esc}</span>')
            break
        # string literal
        if s[i] == '"':
            j = i + 1
            while j < len(s) and s[j] != '"':
                if s[j] == '\\': j += 1
                j += 1
            tok = s[i:j+1].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            parts.append(f'<span class="rtl-string">{tok}</span>')
            i = j + 1; continue
        # preprocessor directive
        if s[i] == '`':
            j = i + 1
            while j < len(s) and (s[j].isalnum() or s[j] == '_'): j += 1
            tok = s[i:j].replace('&','&amp;')
            parts.append(f'<span class="rtl-pp">{tok}</span>')
            i = j; continue
        # number literal: 8'b1010, 4'hF, 32'd0, plain digits
        m = _re.match(r"(\d+('[bodhBODH][0-9a-fA-FxXzZ_]+)?)", s[i:])
        if m and m.group():
            tok = m.group().replace('&','&amp;')
            parts.append(f'<span class="rtl-numlit">{tok}</span>')
            i += len(m.group()); continue
        # identifier / keyword
        if s[i].isalpha() or s[i] in ('_', '$'):
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] in ('_','$')): j += 1
            word = s[i:j]
            esc_w = word.replace('&','&amp;')
            if word in _VL_KW:
                parts.append(f'<span class="rtl-kw">{esc_w}</span>')
            else:
                parts.append(esc_w)
            i = j; continue
        # everything else
        c = s[i]
        parts.append(c.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'))
        i += 1
    return ''.join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# render_code_viewer
# ─────────────────────────────────────────────────────────────────────────────
def render_code_viewer(file_bytes: bytes, records: list, filename=""):
    st.markdown('<div class="sec-header">RTL Code Viewer</div>', unsafe_allow_html=True)
    try:
        src = file_bytes.decode("utf-8", errors="replace")
    except Exception:
        st.warning("Cannot decode source."); return

    lines = src.splitlines()

    # Build per-line risk map: keep highest-risk record, accumulate all signals
    risk_map = {}
    for r in records:
        ln = r.get("line", 0)
        if not ln:
            continue
        sc = r.get("overall_risk", 0)
        if ln not in risk_map or sc > risk_map[ln]["overall_risk"]:
            risk_map[ln] = dict(
                risk_level=r.get("risk_level", ""),
                overall_risk=sc,
                signal=r.get("signal", ""),
                operator=r.get("operator", ""),
                destructive=r.get("destructive_risk", 0),
                intermittent=r.get("intermittent_risk", 0),
                cdc=r.get("cdc_risk", 0),
                power=r.get("power_risk", 0),
                signals=[],
            )
        risk_map[ln]["signals"].append(
            f"{r.get('signal','')} [{r.get('operator','')}]"
        )

    # ── Controls ──────────────────────────────────────────────────────────────
    ctrl1, ctrl2, _ = st.columns([2, 2, 3])
    with ctrl1:
        view_mode = st.selectbox(
            "Show lines",
            ["All lines", "Risky only (>=0.05)", "Medium+ (>=0.3)",
             "High+ (>=0.5)", "Critical only (>=0.75)"],
            key="cv_mode",
        )
    with ctrl2:
        show_hl = st.toggle("Syntax highlighting", value=True, key="cv_hl")

    threshold_map = {
        "All lines": 0.0,
        "Risky only (>=0.05)": 0.05,
        "Medium+ (>=0.3)": 0.30,
        "High+ (>=0.5)": 0.50,
        "Critical only (>=0.75)": 0.75,
    }
    vis_threshold = threshold_map[view_mode]

    # ── Stats bar ─────────────────────────────────────────────────────────────
    n_crit = sum(1 for d in risk_map.values() if d["overall_risk"] >= 0.75)
    n_high = sum(1 for d in risk_map.values() if 0.5  <= d["overall_risk"] < 0.75)
    n_med  = sum(1 for d in risk_map.values() if 0.3  <= d["overall_risk"] < 0.5)
    n_low  = sum(1 for d in risk_map.values() if 0.05 <= d["overall_risk"] < 0.3)
    fname_html = (f'<span style="color:#3b82f6">{filename}</span>'
                  f' &nbsp;&middot;&nbsp; ') if filename else ""
    st.markdown(
        f'<div style="font-size:0.75rem;color:#475569;margin:6px 0 4px;'
        f'display:flex;gap:18px;align-items:center">'
        f'{fname_html}'
        f'<span>{len(lines)} lines</span>'
        f'<span>&middot;</span>'
        f'<span style="color:#ef4444">&#9632; {n_crit} critical</span>'
        f'<span style="color:#f97316">&#9632; {n_high} high</span>'
        f'<span style="color:#eab308">&#9632; {n_med} medium</span>'
        f'<span style="color:#64748b">&#9632; {n_low} low</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Badge config ──────────────────────────────────────────────────────────
    # level_key -> (row_class, badge_bg, badge_fg, label)
    BADGE_CFG = {
        "crit": ("rtl-crit", "#450a0a", "#fca5a5", "CRIT"),
        "high": ("rtl-high", "#431407", "#fdba74", "HIGH"),
        "med":  ("rtl-med",  "#422006", "#fde68a", " MED"),
        "low":  ("rtl-low",  "#1e293b", "#94a3b8", " LOW"),
    }

    def _level_key(sc):
        if sc >= 0.75: return "crit"
        if sc >= 0.50: return "high"
        if sc >= 0.30: return "med"
        if sc >= 0.05: return "low"
        return None

    # ── Build HTML rows ───────────────────────────────────────────────────────
    html_rows = []
    for i, line in enumerate(lines, 1):
        info = risk_map.get(i)
        sc   = info["overall_risk"] if info else 0.0
        lkey = _level_key(sc)

        if vis_threshold > 0 and sc < vis_threshold:
            continue

        row_cls = f"rtl-row {BADGE_CFG[lkey][0]}" if lkey else "rtl-row"

        # Native browser tooltip via title= attribute
        title_attr = ""
        if info and sc >= 0.05:
            sigs_str = " | ".join(dict.fromkeys(info["signals"]))[:120]
            tip = (
                f"Risk: {sc:.4f}  "
                f"({info['risk_level'].split(' ',1)[-1] if info['risk_level'] else ''})\n"
                f"Signal(s): {sigs_str}\n"
                f"Destructive: {info['destructive']:.3f}  "
                f"Intermittent: {info['intermittent']:.3f}  "
                f"CDC: {info['cdc']:.3f}  "
                f"Power: {info['power']:.3f}"
            )
            tip_esc = tip.replace('"', '&quot;').replace("'", '&#39;')
            title_attr = f' title="{tip_esc}"'

        code_html = _hl(line) if show_hl else (
            line.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        )

        badge_html = sig_html = ""
        if lkey:
            _, bg, fg, lbl = BADGE_CFG[lkey]
            badge_html = (
                f'<span class="rtl-badge" style="background:{bg};color:{fg}">'
                f'{lbl} {sc:.2f}</span>'
            )
            sig = (info["signal"] or "")[:18]
            if sig:
                sig_html = f'<span class="rtl-sig">{sig}</span>'

        html_rows.append(
            f'<div class="{row_cls}"{title_attr}>'
            f'<span class="rtl-num">{i}</span>'
            f'<span class="rtl-code">{code_html}</span>'
            f'{sig_html}{badge_html}'
            f'</div>'
        )

    if not html_rows:
        st.info("No lines match the current filter.")
        return

    st.markdown(
        f'<div class="rtl-viewer">{"".join(html_rows)}</div>',
        unsafe_allow_html=True,
    )

    # ── Flagged lines jump list ───────────────────────────────────────────────
    flagged = [
        (ln, d) for ln, d in sorted(risk_map.items())
        if d["overall_risk"] >= 0.3
    ]
    if flagged:
        with st.expander(
            f"Flagged lines ({len(flagged)} — Medium risk and above)",
            expanded=False,
        ):
            jrows = []
            for ln, d in flagged:
                icon = ("🔴" if d["overall_risk"] >= 0.75
                        else ("🟠" if d["overall_risk"] >= 0.5 else "🟡"))
                lvl_label = (d["risk_level"].split(" ", 1)[-1]
                             if d["risk_level"] else "")
                jrows.append({
                    "Line":        ln,
                    "Level":       f"{icon} {lvl_label}",
                    "Score":       round(d["overall_risk"], 4),
                    "Signal":      d["signal"] or "",
                    "Operator":    d["operator"] or "",
                    "Destructive": round(d["destructive"], 3),
                    "Intermittent":round(d["intermittent"], 3),
                    "CDC":         round(d["cdc"], 3),
                    "Power":       round(d["power"], 3),
                })
            jdf = pd.DataFrame(jrows)
            st.dataframe(
                jdf.style.map(_score_color, subset=["Score"]),
                use_container_width=True,
                height=min(300, 40 + len(jrows) * 36),
            )


# ─────────────────────────────────────────────────────────────────────────────
# render_risk_explanation
# ─────────────────────────────────────────────────────────────────────────────
def _explain(row, toggles):
    parts = []
    if row.get("destructive_risk",0) >= 0.5:
        parts.append(f'High <b>destructive risk ({row["destructive_risk"]:.3f})</b> — '
                     'fault here propagates to many downstream signals.')
    if row.get("intermittent_risk",0) >= 0.5:
        parts.append(f'High <b>intermittent risk ({row["intermittent_risk"]:.3f})</b> — '
                     'low execution probability makes this path hard to verify.')
    if row.get("cdc_risk",0) >= 0.4 and row.get("has_cdc_issue", False):
        parts.append(f'<b>CDC risk ({row["cdc_risk"]:.3f})</b> — '
                     'possible clock-domain crossing without synchroniser.')
    if row.get("power_risk",0) >= 0.5:
        tgl = toggles.get(row.get("signal",""), 0)
        parts.append(f'<b>Power risk ({row["power_risk"]:.3f})</b> — '
                     f'signal toggles {tgl}× per window; consider clock gating.')
    if row.get("structural_complexity",0) >= 0.7:
        parts.append(f'<b>Structural complexity ({row["structural_complexity"]:.3f})</b> — '
                     'complex operator or many operands; consider pipelining.')
    return parts or ["Low overall risk across all categories."]

def render_risk_explanation(df, toggles):
    st.markdown('<div class="sec-header">Risk Deep Dive</div>', unsafe_allow_html=True)
    top = df.sort_values("overall_risk", ascending=False).head(10).reset_index(drop=True)

    for row_idx, row in top.iterrows():
        lvl   = row.get("risk_level","")
        score = row.get("overall_risk",0)
        sig   = row.get("signal","")
        line  = row.get("line","")
        raw   = row.get("raw_line","")
        color = {"🔴 Critical":"#ef4444","🟠 High":"#f97316",
                 "🟡 Medium":"#eab308","🟢 Low":"#22c55e"}.get(lvl,"#64748b")

        with st.expander(f"Line {line}  ·  {sig}  ·  {raw[:70]}"):
            left, right = st.columns([3,2])
            with left:
                bullets = "".join(f"<div class='fix-item'>• {p}</div>" for p in _explain(row, toggles))
                st.markdown(f"""
                <div class="fix-card">
                  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                    <span style="font-size:1.2rem;font-weight:700;color:{color}">{score:.3f}</span>
                    <span style="font-size:0.75rem;color:{color};background:{color}22;
                                 padding:2px 10px;border-radius:999px;font-weight:600">
                      {lvl.split(' ',1)[-1]}
                    </span>
                    <span style="font-size:0.72rem;color:#475569">
                      {sig} &nbsp;·&nbsp; {row.get('operator','')}
                    </span>
                  </div>
                  <div class="fix-card-code">{raw}</div>
                  <div style="margin-top:10px;line-height:1.8">{bullets}</div>
                </div>""", unsafe_allow_html=True)

            with right:
                scores = {"Destructive": row.get("destructive_risk",0),
                          "Intermittent": row.get("intermittent_risk",0),
                          "CDC":          row.get("cdc_risk",0),
                          "Power":        row.get("power_risk",0)}
                clrs   = {"Destructive":"#ef4444","Intermittent":"#f97316",
                          "CDC":"#a855f7","Power":"#3b82f6"}
                fig = go.Figure(go.Bar(
                    x=list(scores.values()), y=list(scores.keys()),
                    orientation="h",
                    marker_color=[clrs[k] for k in scores],
                    marker_line_width=0,
                    text=[f"{v:.3f}" for v in scores.values()],
                    textposition="outside",
                    textfont=dict(size=10, color="#94a3b8"),
                ))
                fig.update_layout(
                    paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                    margin=dict(l=4,r=50,t=4,b=4), height=140,
                    xaxis=dict(range=[0,1.1],showgrid=False,
                               showticklabels=False,zeroline=False),
                    yaxis=dict(showgrid=False,tickfont=dict(size=10,color="#94a3b8")),
                    font=dict(color=FONT_COLOR),
                )
                st.plotly_chart(fig, use_container_width=True,
                                key=f"deepdive_{row_idx}")

            fixes = row.get("fix_suggestion","")
            if fixes:
                st.markdown(
                    '<div style="font-size:0.7rem;font-weight:600;color:#475569;'
                    'text-transform:uppercase;letter-spacing:0.6px;'
                    'margin:8px 0 5px">Recommended Fixes</div>',
                    unsafe_allow_html=True)
                for f in fixes.split(" | "):
                    if f.strip():
                        st.markdown(f'<div class="fix-item">→ {f.strip()}</div>',
                                    unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# render_lint_panel
# ─────────────────────────────────────────────────────────────────────────────
def render_lint_panel(lint_df):
    st.markdown('<div class="sec-header">Lint Checker — 20 Rules</div>',
                unsafe_allow_html=True)
    if lint_df.empty:
        st.success("✅ No lint violations found."); return

    err  = lint_df[lint_df["severity"].str.contains("Error",   na=False)]
    warn = lint_df[lint_df["severity"].str.contains("Warning", na=False)]
    info = lint_df[lint_df["severity"].str.contains("Info",    na=False)]

    lc1, lc2, lc3 = st.columns(3)
    for col, n, lbl, color, sub in [
        (lc1, len(err),  "Errors",   "#ef4444","Must fix before synthesis"),
        (lc2, len(warn), "Warnings", "#f97316","Recommended to fix"),
        (lc3, len(info), "Info",     "#eab308","Advisory notices"),
    ]:
        with col:
            st.markdown(f"""
            <div class="mcard">
              <div class="mcard-accent" style="background:{color}"></div>
              <div class="mcard-label">{lbl}</div>
              <div class="mcard-value" style="color:{color}">{n}</div>
              <div class="mcard-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    fc1, fc2 = st.columns(2)
    with fc1:
        sev_sel  = st.selectbox("Severity", ["All"]+sorted(lint_df["severity"].unique().tolist()), key="lsev")
    with fc2:
        rule_sel = st.selectbox("Rule ID",  ["All"]+sorted(lint_df["rule_id"].unique().tolist()),  key="lrule")

    flt = lint_df.copy()
    if sev_sel  != "All": flt = flt[flt["severity"]==sev_sel]
    if rule_sel != "All": flt = flt[flt["rule_id"] ==rule_sel]
    st.caption(f"{len(flt)} of {len(lint_df)} violations shown")

    for _, row in flt.iterrows():
        sev = row.get("severity","")
        ico = "🔴" if "Error" in sev else ("🟠" if "Warning" in sev else "🟡")
        with st.expander(f"{ico} [{row.get('rule_id','')}]  Line {row.get('line',0)}  —  {row.get('message','')}"):
            st.code(row.get("raw_line",""), language="verilog")
            st.markdown(f'<div style="color:#3b82f6;font-size:0.8rem;margin-top:4px">🔧 {row.get("fix","")}</div>',
                        unsafe_allow_html=True)

    svc = lint_df["severity"].value_counts().reset_index()
    svc.columns = ["Severity","Count"]
    fig = px.bar(svc, x="Severity", y="Count",
                 color="Severity", text="Count",
                 color_discrete_map={"🔴 Error":"#ef4444","🟠 Warning":"#f97316","🟡 Info":"#eab308"})
    fig.update_traces(textposition="outside", marker_line_width=0)
    _chart(fig, "Violations by Severity", 240)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# render_cdc_panel
# ─────────────────────────────────────────────────────────────────────────────
def render_cdc_panel(df, rtl):
    st.markdown('<div class="sec-header">Clock Domain Crossing (CDC)</div>',
                unsafe_allow_html=True)
    cdc = df[df["has_cdc_issue"]==True] if "has_cdc_issue" in df.columns else pd.DataFrame()

    cc1, cc2, cc3 = st.columns(3)
    for col, n, lbl, color, sub in [
        (cc1, max(len(rtl.clock_signals),1), "Clock Domains","#a855f7",', '.join(rtl.clock_signals) or "none"),
        (cc2, len(cdc),                      "CDC Ops",       "#f97316","Flagged for sync review"),
        (cc3, len(rtl.reset_signals),        "Reset Signals", "#22c55e",', '.join(rtl.reset_signals) or "none"),
    ]:
        with col:
            st.markdown(f"""
            <div class="mcard">
              <div class="mcard-accent" style="background:{color}"></div>
              <div class="mcard-label">{lbl}</div>
              <div class="mcard-value" style="color:{color}">{n}</div>
              <div class="mcard-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    if not cdc.empty:
        cols = [c for c in ["line","signal","raw_line","cdc_risk","susceptibility"] if c in cdc.columns]
        st.dataframe(cdc[cols].sort_values("cdc_risk",ascending=False)
                              .style.format({"cdc_risk":"{:.4f}","susceptibility":"{:.4f}"}),
                     use_container_width=True, height=220)
        fig = px.bar(cdc.sort_values("cdc_risk",ascending=False).head(15),
                     x="signal", y="cdc_risk", color="cdc_risk", text="cdc_risk",
                     color_continuous_scale=["#1e1b4b","#a855f7","#ef4444"])
        fig.update_traces(texttemplate="%{text:.3f}", textposition="outside",
                          marker_line_width=0)
        _chart(fig, "CDC Risk per Signal", 280)
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ No CDC-flagged operations detected.")


# ─────────────────────────────────────────────────────────────────────────────
# render_metrics_panel
# ─────────────────────────────────────────────────────────────────────────────
def render_metrics_panel(df, rtl):
    st.markdown('<div class="sec-header">Signal Metrics</div>', unsafe_allow_html=True)

    mc1, mc2 = st.columns(2)
    with mc1:
        tdf = (pd.DataFrame([{"Type":s.signal_type} for s in rtl.signals.values()])
               ["Type"].value_counts().reset_index())
        tdf.columns = ["Type","Count"]
        fig = px.pie(tdf, names="Type", values="Count", hole=0.5,
                     color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_traces(textinfo="percent+label",
                          marker=dict(line=dict(color="#0d1424",width=2)))
        _chart(fig, "Signal Types", 280)
        fig.update_layout(showlegend=False, plot_bgcolor=CHART_BG)
        st.plotly_chart(fig, use_container_width=True)
    with mc2:
        wdf = pd.DataFrame([{"Signal":n,"Width":s.width,"Type":s.signal_type}
                             for n,s in rtl.signals.items()]).sort_values("Width",ascending=False)
        fig2 = px.bar(wdf.head(20), x="Signal", y="Width", color="Type",
                      color_discrete_sequence=px.colors.qualitative.Set3)
        fig2.update_traces(marker_line_width=0)
        _chart(fig2, "Signal Bit-Widths (Top 20)", 280)
        st.plotly_chart(fig2, use_container_width=True)

    met = ["signal","initial_weight","impact_score","susceptibility",
           "execution_probability","structural_complexity"]
    avail = [c for c in met if c in df.columns]
    mdf = df[avail].drop_duplicates("signal").sort_values("impact_score",ascending=False)
    st.dataframe(mdf.style.background_gradient(subset=avail[1:], cmap="Blues"),
                 use_container_width=True, height=280)

    heat = mdf.set_index("signal")[avail[1:]].apply(pd.to_numeric, errors="coerce")
    fig3 = px.imshow(heat.T, color_continuous_scale="Blues",
                     aspect="auto", text_auto=".2f")
    fig3.update_coloraxes(showscale=False)
    _chart(fig3, "Metrics Heatmap", 220)
    fig3.update_layout(plot_bgcolor=CHART_BG)
    st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# render_dependency_graph
# ─────────────────────────────────────────────────────────────────────────────
def render_dependency_graph(graph, rtl):
    st.markdown('<div class="sec-header">Signal Dependency Graph</div>',
                unsafe_allow_html=True)
    G = graph.graph
    if not G.nodes:
        st.info("No dependency data available for this module."); return

    # ── Pre-compute node metrics ──────────────────────────────────────────────
    nodes = list(G.nodes)
    centrality = nx.betweenness_centrality(G) if len(nodes) >= 3 else {n: 0.0 for n in nodes}
    # Normalise centrality to [0,1]
    max_c = max(centrality.values()) or 1.0
    cent_norm = {n: v / max_c for n, v in centrality.items()}

    fanout = {n: G.out_degree(n) for n in nodes}
    fanin  = {n: G.in_degree(n)  for n in nodes}

    # ── Controls ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        layout_choice = st.selectbox(
            "Layout",
            ["Spring (force-directed)", "Kamada-Kawai", "Hierarchical (dot)", "Circular", "Shell"],
            key="dg_layout",
        )
    with c2:
        color_by = st.selectbox(
            "Color nodes by",
            ["Signal type", "Centrality", "Fan-out", "Fan-in"],
            key="dg_color",
        )
    with c3:
        highlight_sig = st.selectbox(
            "Highlight signal path",
            ["None"] + sorted(nodes),
            key="dg_hl",
        )
    with c4:
        show_labels = st.toggle("Show labels", value=True, key="dg_lbl")

    # ── Compute layout positions ──────────────────────────────────────────────
    try:
        if layout_choice.startswith("Spring"):
            k_val = 3.5 / (len(nodes) ** 0.5) if len(nodes) > 4 else 2.2
            pos = nx.spring_layout(G, seed=42, k=k_val, iterations=80)
        elif layout_choice.startswith("Kamada"):
            pos = nx.kamada_kawai_layout(G)
        elif layout_choice.startswith("Hierarchical"):
            try:
                pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
                # Normalize to [-1,1]
                xs = [v[0] for v in pos.values()]; ys = [v[1] for v in pos.values()]
                rx = max(xs)-min(xs) or 1; ry = max(ys)-min(ys) or 1
                pos = {n: ((x-min(xs))/rx*2-1, (y-min(ys))/ry*2-1) for n,(x,y) in pos.items()}
            except Exception:
                pos = nx.spring_layout(G, seed=42, k=2.2)
        elif layout_choice.startswith("Circular"):
            pos = nx.circular_layout(G)
        else:
            pos = nx.shell_layout(G)
    except Exception:
        pos = nx.spring_layout(G, seed=42)

    # ── Determine highlighted path nodes/edges ────────────────────────────────
    hl_nodes: set = set()
    hl_edges: set = set()
    if highlight_sig != "None" and highlight_sig in G:
        hl_nodes.add(highlight_sig)
        # upstream (ancestors) + downstream (descendants)
        try:
            hl_nodes |= nx.ancestors(G, highlight_sig)
            hl_nodes |= nx.descendants(G, highlight_sig)
        except Exception:
            pass
        for u, v in G.edges():
            if u in hl_nodes and v in hl_nodes:
                hl_edges.add((u, v))

    # ── Color palette ─────────────────────────────────────────────────────────
    TYPE_COLORS = {
        "input":        "#22c55e",
        "output":       "#ef4444",
        "inout":        "#f97316",
        "wire":         "#3b82f6",
        "reg":          "#a855f7",
        "logic":        "#8b5cf6",
        "unknown":      "#475569",
    }

    def _type_color(n):
        sig = rtl.signals.get(n)
        if sig:
            for key, col in TYPE_COLORS.items():
                if key in sig.signal_type:
                    return col
        return "#475569"

    def _centrality_color(n):
        v = cent_norm.get(n, 0)
        if v >= 0.75: return "#ef4444"
        if v >= 0.50: return "#f97316"
        if v >= 0.25: return "#eab308"
        return "#3b82f6"

    def _fanout_color(n):
        fo = fanout.get(n, 0)
        if fo >= 6: return "#ef4444"
        if fo >= 3: return "#f97316"
        if fo >= 1: return "#3b82f6"
        return "#475569"

    def _fanin_color(n):
        fi = fanin.get(n, 0)
        if fi >= 6: return "#a855f7"
        if fi >= 3: return "#8b5cf6"
        if fi >= 1: return "#3b82f6"
        return "#475569"

    color_fn = {
        "Signal type":  _type_color,
        "Centrality":   _centrality_color,
        "Fan-out":      _fanout_color,
        "Fan-in":       _fanin_color,
    }[color_by]

    # ── Build Plotly figure ───────────────────────────────────────────────────
    # --- Edge traces (dimmed + highlighted) ----------------------------------
    ex_dim, ey_dim = [], []
    ex_hl,  ey_hl  = [], []

    for u, v in G.edges():
        x0, y0 = pos[u]; x1, y1 = pos[v]
        bucket_x = ex_hl if (u, v) in hl_edges else ex_dim
        bucket_y = ey_hl if (u, v) in hl_edges else ey_dim
        bucket_x += [x0, x1, None]
        bucket_y += [y0, y1, None]

    traces = []
    if ex_dim:
        traces.append(go.Scatter(
            x=ex_dim, y=ey_dim, mode="lines",
            line=dict(width=0.8, color="#1e3a5f"),
            hoverinfo="none", showlegend=False,
        ))
    if ex_hl:
        traces.append(go.Scatter(
            x=ex_hl, y=ey_hl, mode="lines",
            line=dict(width=2.5, color="#f59e0b"),
            hoverinfo="none", showlegend=False,
        ))

    # --- Arrowhead annotations -----------------------------------------------
    annotations = []
    for u, v in G.edges():
        x0, y0 = pos[u]; x1, y1 = pos[v]
        is_hl_edge = (u, v) in hl_edges
        annotations.append(dict(
            ax=x0, ay=y0, x=x1, y=y1,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True,
            arrowhead=3, arrowsize=1.0,
            arrowwidth=1.5 if is_hl_edge else 0.8,
            arrowcolor="#f59e0b" if is_hl_edge else "#1e3a5f",
            standoff=10,
        ))

    # --- Node trace -----------------------------------------------------------
    node_x = [pos[n][0] for n in nodes]
    node_y = [pos[n][1] for n in nodes]

    node_colors, node_sizes, node_borders, border_widths = [], [], [], []
    hover_texts = []

    for n in nodes:
        sig = rtl.signals.get(n)
        c   = cent_norm.get(n, 0)
        fo  = fanout.get(n, 0)
        fi  = fanin.get(n, 0)

        base_color = color_fn(n)
        is_hl = n in hl_nodes and highlight_sig != "None"
        is_focus = n == highlight_sig

        node_colors.append(base_color)
        # Size: base 14 + centrality boost + highlight boost
        size = 14 + c * 20 + (8 if is_focus else (4 if is_hl else 0))
        node_sizes.append(size)
        node_borders.append("#f59e0b" if is_focus else
                            ("#fbbf24" if is_hl else "#0d1424"))
        border_widths.append(3 if is_focus else (2 if is_hl else 1.2))

        # Hover tooltip
        stype = sig.signal_type if sig else "unknown"
        width = sig.width       if sig else 1
        tip = (
            f"<b>{n}</b><br>"
            f"Type: {stype} &nbsp;·&nbsp; Width: [{width-1}:0]<br>"
            f"Fan-out: {fo} &nbsp;·&nbsp; Fan-in: {fi}<br>"
            f"Centrality: {c:.4f}<br>"
        )
        if fo > 0:
            tip += "Drives: " + ", ".join(list(G.successors(n))[:6]) + "<br>"
        if fi > 0:
            tip += "Driven by: " + ", ".join(list(G.predecessors(n))[:6])
        hover_texts.append(tip)

    traces.append(go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text" if show_labels else "markers",
        text=nodes if show_labels else [],
        textposition="top center",
        textfont=dict(size=9, color="#94a3b8"),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(color=node_borders, width=border_widths),
            opacity=0.95,
        ),
        hovertext=hover_texts,
        hoverinfo="text",
        hoverlabel=dict(
            bgcolor="#0f172a",
            bordercolor="#3b82f6",
            font=dict(color="#e2e8f0", size=12, family="Inter"),
        ),
        showlegend=False,
    ))

    # ── Legend annotation ─────────────────────────────────────────────────────
    if color_by == "Signal type":
        legend_items = [
            ("Input",    "#22c55e"), ("Output", "#ef4444"),
            ("Inout",    "#f97316"), ("Wire",  "#3b82f6"),
            ("Reg",      "#a855f7"), ("Unknown","#475569"),
        ]
    elif color_by == "Centrality":
        legend_items = [
            ("Critical (≥0.75)", "#ef4444"), ("High (≥0.50)", "#f97316"),
            ("Medium (≥0.25)",   "#eab308"), ("Low",          "#3b82f6"),
        ]
    elif color_by == "Fan-out":
        legend_items = [
            ("Fan-out ≥6", "#ef4444"), ("Fan-out ≥3", "#f97316"),
            ("Fan-out ≥1", "#3b82f6"), ("Sink",       "#475569"),
        ]
    else:
        legend_items = [
            ("Fan-in ≥6",  "#a855f7"), ("Fan-in ≥3", "#8b5cf6"),
            ("Fan-in ≥1",  "#3b82f6"), ("Source",    "#475569"),
        ]
    legend_html = " &nbsp; ".join(
        f'<span style="color:{c}">&#9679;</span>'
        f'<span style="color:#64748b;font-size:0.7rem"> {lbl}</span>'
        for lbl, c in legend_items
    )

    fig = go.Figure(
        data=traces,
        layout=go.Layout(
            title=dict(
                text=f"Signal Dependency Graph &nbsp;·&nbsp; "
                     f"<span style='font-size:0.75em;color:#475569'>"
                     f"{len(nodes)} nodes · {G.number_of_edges()} edges · "
                     f"{layout_choice.split('(')[0].strip()}</span>",
                font=dict(size=13, color="#cbd5e1"),
                x=0,
            ),
            annotations=annotations,
            showlegend=False,
            paper_bgcolor=CHART_BG,
            plot_bgcolor="#0a0f1e",
            font=dict(color=FONT_COLOR),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                       scaleanchor="y"),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=16, r=16, t=48, b=16),
            height=540,
            dragmode="pan",
            hovermode="closest",
        ),
    )

    # Config: enable scroll-zoom + reset-axes button
    config = dict(
        scrollZoom=True,
        displayModeBar=True,
        modeBarButtonsToRemove=["select2d", "lasso2d"],
        displaylogo=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=config,
                    key="dep_graph")
    st.markdown(
        f'<div style="font-size:0.72rem;margin:-10px 0 16px 4px">{legend_html}</div>',
        unsafe_allow_html=True,
    )

    # ── Stats + critical nodes table ──────────────────────────────────────────
    s1, s2 = st.columns([3, 2])

    with s1:
        crit_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:12]
        if crit_nodes:
            cdf = pd.DataFrame([{
                "Signal":      n,
                "Centrality":  round(c, 5),
                "Type":        (rtl.signals[n].signal_type if n in rtl.signals else "unknown"),
                "Fan-out":     fanout[n],
                "Fan-in":      fanin[n],
                "Downstream":  len(graph.get_downstream_signals(n)),
            } for n, c in crit_nodes])
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:600;color:#475569;'
                'text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">'
                'Most Critical Signals (by Betweenness Centrality)</div>',
                unsafe_allow_html=True,
            )
            st.dataframe(
                cdf.style.bar(subset=["Centrality"], color="#3b82f6")
                         .bar(subset=["Fan-out"],    color="#ef4444")
                         .bar(subset=["Downstream"], color="#a855f7")
                         .format({"Centrality": "{:.5f}"}),
                use_container_width=True,
                height=min(380, 40 + len(cdf) * 36),
            )

    with s2:
        # Node type distribution
        type_counts: dict = {}
        for n in nodes:
            sig = rtl.signals.get(n)
            t = "unknown"
            if sig:
                for key in ("input","output","inout","wire","reg","logic"):
                    if key in sig.signal_type:
                        t = key; break
            type_counts[t] = type_counts.get(t, 0) + 1

        tc_df = pd.DataFrame(
            [{"Type": k.capitalize(), "Count": v} for k, v in type_counts.items()]
        )
        fig_tc = px.bar(
            tc_df, x="Count", y="Type", orientation="h",
            color="Type",
            color_discrete_map={
                k.capitalize(): TYPE_COLORS.get(k, "#475569")
                for k in type_counts
            },
            text="Count",
        )
        fig_tc.update_traces(textposition="outside", marker_line_width=0)
        _chart(fig_tc, "Node Type Distribution", 220)
        fig_tc.update_layout(showlegend=False, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_tc, use_container_width=True, key="dep_type_dist")

        # Fan-out histogram
        fo_vals = list(fanout.values())
        fig_fo = px.histogram(
            x=fo_vals, nbins=max(fo_vals) + 1 if fo_vals else 10,
            color_discrete_sequence=["#3b82f6"],
            labels={"x": "Fan-out", "y": "Signals"},
        )
        fig_fo.update_traces(marker_line_color="#1e293b", marker_line_width=1)
        _chart(fig_fo, "Fan-out Distribution", 180)
        fig_fo.update_layout(xaxis_title="Fan-out", yaxis_title="Count")
        st.plotly_chart(fig_fo, use_container_width=True, key="dep_fanout_hist")

    # ── Signal path explorer ──────────────────────────────────────────────────
    if highlight_sig != "None":
        with st.expander(
            f"Path Explorer — {highlight_sig}  "
            f"({len(hl_nodes)-1} connected signals)",
            expanded=True,
        ):
            up_col, dn_col = st.columns(2)
            with up_col:
                up = sorted(graph.get_upstream_signals(highlight_sig))
                st.markdown(
                    f'<div style="font-size:0.72rem;font-weight:600;color:#22c55e;'
                    f'text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">'
                    f'&#8593; Upstream ({len(up)})</div>',
                    unsafe_allow_html=True,
                )
                for s in up[:30]:
                    stype = rtl.signals[s].signal_type if s in rtl.signals else "unknown"
                    st.markdown(
                        f'<div style="font-size:0.79rem;color:#94a3b8;padding:2px 0">'
                        f'<span style="color:#22c55e">&#8594;</span> '
                        f'<b>{s}</b> <span style="color:#475569">{stype}</span></div>',
                        unsafe_allow_html=True,
                    )
            with dn_col:
                dn = sorted(graph.get_downstream_signals(highlight_sig))
                st.markdown(
                    f'<div style="font-size:0.72rem;font-weight:600;color:#ef4444;'
                    f'text-transform:uppercase;letter-spacing:0.8px;margin-bottom:6px">'
                    f'&#8595; Downstream ({len(dn)})</div>',
                    unsafe_allow_html=True,
                )
                for s in dn[:30]:
                    stype = rtl.signals[s].signal_type if s in rtl.signals else "unknown"
                    st.markdown(
                        f'<div style="font-size:0.79rem;color:#94a3b8;padding:2px 0">'
                        f'<span style="color:#ef4444">&#8594;</span> '
                        f'<b>{s}</b> <span style="color:#475569">{stype}</span></div>',
                        unsafe_allow_html=True,
                    )


# ─────────────────────────────────────────────────────────────────────────────
# render_export
# ─────────────────────────────────────────────────────────────────────────────
def render_export(df, lint_df, rtl, health, records, lint_violations, toggles):
    st.markdown('<div class="sec-header">Export Reports</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Risk Analysis CSV", df.to_csv(index=False),
                           "rtl_risk_report.csv","text/csv", use_container_width=True)
    with c2:
        if not lint_df.empty:
            st.download_button("⬇️ Lint Violations CSV", lint_df.to_csv(index=False),
                               "rtl_lint_report.csv","text/csv", use_container_width=True)
        else:
            st.button("⬇️ Lint CSV (none)", disabled=True, use_container_width=True)
    with c3:
        try:
            from analyzer.pdf_report import generate_pdf_report
            pdf = generate_pdf_report(module_name=rtl.module_name, health=health,
                                      records=records, lint_violations=lint_violations,
                                      rtl_signals=rtl.signals, toggles=toggles)
            st.download_button("📄 Full PDF Report", pdf,
                               f"{rtl.module_name}_rtl_report.pdf",
                               "application/pdf", use_container_width=True)
        except Exception as ex:
            st.error(f"PDF error: {ex}")


# ─────────────────────────────────────────────────────────────────────────────
# render_sidebar
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:16px 0 10px">
          <div style="font-size:1.05rem;font-weight:700;color:#f1f5f9">RTL Analyzer</div>
          <div style="font-size:0.72rem;color:#475569;margin-top:2px">
            Verilog / SystemVerilog
          </div>
        </div>
        <hr style="border-color:#1e293b;margin:4px 0 18px">
        """, unsafe_allow_html=True)

        st.markdown('<div style="font-size:0.72rem;font-weight:600;color:#475569;'
                    'text-transform:uppercase;letter-spacing:0.8px;'
                    'margin-bottom:8px">Upload File</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("Verilog / .SV", type=["v","sv"],
                                    label_visibility="collapsed",
                                    key="file_uploader")

        st.markdown('<div style="font-size:0.72rem;font-weight:600;color:#475569;'
                    'text-transform:uppercase;letter-spacing:0.8px;'
                    'margin:18px 0 8px">Demo Samples</div>', unsafe_allow_html=True)
        use_alu  = st.button("▶ ALU sample",        use_container_width=True)
        use_mips = st.button("▶ MIPS Pipeline",     use_container_width=True)

        # Clear button — only shown when a file is loaded
        if st.session_state.get("loaded_file_bytes"):
            st.markdown('<hr style="border-color:#1e293b;margin:10px 0">', unsafe_allow_html=True)
            if st.button("❌  Clear / Load new file", use_container_width=True):
                st.session_state.pop("loaded_file_bytes", None)
                st.session_state.pop("loaded_filename",   None)
                st.rerun()

        st.markdown('<hr style="border-color:#1e293b;margin:18px 0">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.72rem;font-weight:600;color:#475569;'
                    'text-transform:uppercase;letter-spacing:0.8px;'
                    'margin-bottom:8px">Filters</div>', unsafe_allow_html=True)
        risk_threshold = st.slider("Risk threshold", 0.0, 1.0, 0.3, 0.05,
                                   help="Only show operations at or above this score")
        show_all       = st.toggle("Show all operations", value=False,
                                   help="Override threshold and show every operation")
        waveform_cycles = st.slider("Waveform cycles", 8, 128, 64, 8)

        st.markdown('<hr style="border-color:#1e293b;margin:18px 0">', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.68rem;color:#334155;line-height:1.7">'
            '20 LINT rules &nbsp;·&nbsp; CDC detection<br>'
            'Power / toggle analysis &nbsp;·&nbsp; PDF export'
            '</div>',
            unsafe_allow_html=True,
        )

    return uploaded, use_alu, use_mips, risk_threshold, waveform_cycles, show_all


# ─────────────────────────────────────────────────────────────────────────────
# render_landing
# ─────────────────────────────────────────────────────────────────────────────
def render_landing():
    st.markdown("""
    <div style="max-width:680px;margin:60px auto;text-align:center">
      <div style="font-size:3.5rem;margin-bottom:12px">🔬</div>
      <div style="font-size:1.6rem;font-weight:700;color:#f1f5f9;margin-bottom:10px">
        RTL Health Analyzer
      </div>
      <div style="font-size:0.9rem;color:#475569;line-height:1.9;margin-bottom:36px">
        Upload a Verilog <code style="background:#1e293b;padding:1px 6px;
        border-radius:4px;color:#93c5fd">.v</code> or SystemVerilog
        <code style="background:#1e293b;padding:1px 6px;border-radius:4px;
        color:#93c5fd">.sv</code> file, or load a demo from the sidebar.
      </div>
    </div>""", unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    for col,(color,icon,title,desc) in zip(
        [c1,c2,c3,c4,c5],
        [("#ef4444","💥","Destructive","Impact & propagation"),
         ("#f97316","🎲","Intermittent","Exec probability"),
         ("#a855f7","⚡","CDC","Clock domains"),
         ("#3b82f6","🔋","Power","Toggle analysis"),
         ("#22c55e","🪲","Lint","20-rule checker")],
    ):
        with col:
            st.markdown(f"""
            <div class="mcard" style="text-align:center">
              <div class="mcard-accent" style="background:{color}"></div>
              <div style="font-size:1.6rem;margin:8px 0 4px">{icon}</div>
              <div style="font-size:0.82rem;font-weight:600;color:#e2e8f0">{title}</div>
              <div style="font-size:0.7rem;color:#475569;margin-top:3px">{desc}</div>
            </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    uploaded, use_alu, use_mips, risk_threshold, waveform_cycles, show_all = \
        render_sidebar()

    base_dir = os.path.join(os.path.dirname(__file__), "..", "samples")

    # ── Persist the loaded file in session_state so widget reruns don’t lose it ──
    # Priority: new upload > demo button > existing session state
    if uploaded is not None:
        st.session_state["loaded_file_bytes"] = uploaded.getvalue()
        st.session_state["loaded_filename"]   = uploaded.name
    elif use_alu:
        with open(os.path.join(base_dir, "alu.v"), "rb") as f:
            st.session_state["loaded_file_bytes"] = f.read()
        st.session_state["loaded_filename"] = "alu.v"
    elif use_mips:
        with open(os.path.join(base_dir, "mips_pipeline.v"), "rb") as f:
            st.session_state["loaded_file_bytes"] = f.read()
        st.session_state["loaded_filename"] = "mips_pipeline.v"

    file_bytes = st.session_state.get("loaded_file_bytes")
    filename   = st.session_state.get("loaded_filename", "")

    if file_bytes is None:
        render_header()
        render_landing()
        return

    with st.spinner("Running RTL analysis pipeline…"):
        try:
            rtl, graph, records, health, lint_violations, waveforms, toggles = \
                _run_analysis(file_bytes)
        except Exception as ex:
            render_header()
            st.error(f"Analysis failed: {ex}"); return

    render_header(rtl.module_name)

    df      = pd.DataFrame(records)
    lint_df = pd.DataFrame(lint_violations) if lint_violations else pd.DataFrame()
    df_risk = df if show_all else df[df["overall_risk"] >= risk_threshold]

    st.markdown(
        f'<div style="background:#052e16;border:1px solid #166534;border-radius:8px;'
        f'padding:10px 18px;color:#86efac;font-size:0.84rem;margin-bottom:20px">'
        f'✅ &nbsp;Analysis complete &nbsp;·&nbsp; <b>{filename}</b>'
        f'&nbsp;·&nbsp; {len(records)} operations'
        f'&nbsp;·&nbsp; {len(rtl.signals)} signals'
        f'&nbsp;·&nbsp; {len(lint_violations)} lint violations</div>',
        unsafe_allow_html=True,
    )

    render_health_gauge(health, df)
    st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
    render_summary_cards(df, health, lint_violations, rtl)
    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)

    tabs = st.tabs([
        "📊  Risk Rankings",
        "📈  Visualizations",
        "🔬  Code Viewer",
        "💡  Risk Deep Dive",
        "🪲  Lint",
        "⚡  CDC",
        "📐  Metrics",
        "🕸️  Dependency",
        "📥  Export",
    ])
    with tabs[0]: render_risk_tables(df_risk)
    with tabs[1]: render_charts(df, toggles, waveform_cycles, waveforms)
    with tabs[2]: render_code_viewer(file_bytes, records, filename)
    with tabs[3]: render_risk_explanation(df, toggles)
    with tabs[4]: render_lint_panel(lint_df)
    with tabs[5]: render_cdc_panel(df, rtl)
    with tabs[6]: render_metrics_panel(df, rtl)
    with tabs[7]: render_dependency_graph(graph, rtl)
    with tabs[8]: render_export(df, lint_df, rtl, health, records, lint_violations, toggles)


main()
