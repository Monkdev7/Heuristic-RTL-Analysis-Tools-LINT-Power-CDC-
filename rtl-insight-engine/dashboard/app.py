"""
RTL Insight Engine v2 — Advanced Streamlit Dashboard
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


@st.cache_data(show_spinner=False)
def _run_analysis(file_bytes: bytes):
    """Cache RTL analysis by file content — avoids re-running on every slider change."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.v', mode='wb') as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return analyze_rtl(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RTL Insight Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main-title {
    font-size:2.5rem;font-weight:900;
    background:linear-gradient(90deg,#667eea,#764ba2);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  }
  .subtitle { color:#888;font-size:1rem; }
  div[data-testid="stMetric"] {
    background:rgba(102,126,234,0.08);border-radius:12px;padding:12px;
  }
  .lint-error   { color:#ef4444;font-weight:bold; }
  .lint-warning { color:#f97316;font-weight:bold; }
  .lint-info    { color:#eab308; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ RTL Insight Engine")
    st.markdown("*v2.0 — Advanced RTL Analysis*")
    st.divider()

    uploaded = st.file_uploader(
        "📂 Upload Verilog/SV File",
        type=['v', 'sv', 'vh']
    )
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        use_alu = st.button("🎮 ALU Demo", use_container_width=True)
    with col_s2:
        use_mips = st.button("🖥️ MIPS Demo", use_container_width=True)

    st.divider()
    st.markdown("### ⚙️ Options")
    show_all      = st.checkbox("Show All Signals", False)
    risk_threshold = st.slider("Risk Threshold", 0.0, 1.0, 0.3, 0.05)
    waveform_cycles = st.slider("Waveform Cycles", 16, 64, 32, 8)

# ── Load file ────────────────────────────────────────────────────────────────
filepath = None
base_dir = os.path.join(os.path.dirname(__file__), '..', 'samples')

if use_alu:
    filepath = os.path.join(base_dir, 'alu.v')
if use_mips:
    filepath = os.path.join(base_dir, 'mips_pipeline.v')
if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.v', mode='wb') as f:
        f.write(uploaded.getvalue())
        filepath = f.name

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">⚡ RTL Insight Engine</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Unified Lint · CDC · Power · Waveform Analyzer for Verilog/SystemVerilog</p>',
            unsafe_allow_html=True)
st.divider()

# ── Analysis ─────────────────────────────────────────────────────────────────
if filepath:
    with st.spinner("🔍 Running full RTL analysis pipeline..."):
        try:
            with open(filepath, 'rb') as _fh:
                _fbytes = _fh.read()
            rtl, graph, records, health, lint_violations, waveforms, toggles = _run_analysis(_fbytes)
        except Exception as e:
            st.error(f"Analysis error: {e}")
            st.stop()

    df = pd.DataFrame(records)
    lint_df = pd.DataFrame(lint_violations) if lint_violations else pd.DataFrame()
    df_risk = df[df['overall_risk'] >= risk_threshold] if not show_all else df

    # ── Health Banner ────────────────────────────────────────────────────────
    st.markdown("## 🏥 RTL Health Dashboard")

    hc_map = {'green':'#22c55e','orange':'#f97316','darkorange':'#ea580c','red':'#ef4444'}
    hc = hc_map.get(health['color'], '#888')

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{hc}22,{hc}44);
                    border:2px solid {hc};border-radius:16px;
                    padding:20px;text-align:center">
          <div style="font-size:2.8rem;font-weight:900;color:{hc}">{health['score']}</div>
          <div style="color:{hc};font-weight:600">Health Score</div>
          <div style="color:#aaa;font-size:0.8rem">{health['grade']}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.metric("📊 Operations", len(records))
    with c3:
        st.metric("🔴 Critical", health.get('critical_count', 0))
    with c4:
        st.metric("🟠 High Risk", health.get('high_count', 0))
    with c5:
        st.metric("🪲 Lint Issues", len(lint_violations))
    with c6:
        st.metric("📡 Signals", len(rtl.signals))

    st.divider()

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🎯 Risk Overview",
        "🪲 Lint Checker",
        "📊 Metrics",
        "🌊 Waveform",
        "🕸️ Dependency",
        "⚡ CDC",
        "💡 Fix Suggestions"
    ])

    # ── Tab 1: Risk Overview ─────────────────────────────────────────────────
    with tab1:
        st.markdown("### 🎯 Risk Violations Table")

        sf1, sf2 = st.columns([3, 1])
        with sf1:
            sig_search = st.text_input("🔍 Filter by signal name", "", key="sig_search")
        with sf2:
            op_opts = ["All"] + sorted(df_risk['operator'].unique().tolist())
            op_sel  = st.selectbox("Operator", op_opts, key="op_sel")

        filtered_risk = df_risk.copy()
        if sig_search:
            filtered_risk = filtered_risk[
                filtered_risk['signal'].str.contains(sig_search, case=False, na=False)
            ]
        if op_sel != "All":
            filtered_risk = filtered_risk[filtered_risk['operator'] == op_sel]

        def highlight_risk(val):
            return {
                '🔴 Critical':'background-color:#ef444420;color:#ef4444;font-weight:bold',
                '🟠 High':'background-color:#f9731620;color:#f97316;font-weight:bold',
                '🟡 Medium':'background-color:#eab30820;color:#eab308',
                '🟢 Low':'background-color:#22c55e20;color:#22c55e'
            }.get(val,'')

        disp = ['line','raw_line','signal','operator','overall_risk',
                'destructive_risk','intermittent_risk','cdc_risk','power_risk','risk_level']
        avail = [c for c in disp if c in filtered_risk.columns]
        top_df = filtered_risk[avail].sort_values('overall_risk', ascending=False).head(50)
        st.dataframe(
            top_df.style.map(highlight_risk, subset=['risk_level']),
            use_container_width=True, height=380
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            risk_data = pd.DataFrame({
                'Risk Type': ['Destructive','Intermittent','CDC','Power'],
                'Score': [df['destructive_risk'].mean(), df['intermittent_risk'].mean(),
                          df['cdc_risk'].mean(), df['power_risk'].mean()]
            })
            fig = px.bar(risk_data, x='Risk Type', y='Score',
                         color='Score',
                         color_continuous_scale=['#22c55e','#eab308','#f97316','#ef4444'],
                         title="Average Risk by Category")
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig, use_container_width=True)

        with col_b2:
            counts = df['risk_level'].value_counts().reset_index()
            counts.columns = ['Level','Count']
            fig2 = px.pie(counts, names='Level', values='Count',
                          title="Risk Distribution",
                          color='Level',
                          color_discrete_map={
                              '🔴 Critical':'#ef4444','🟠 High':'#f97316',
                              '🟡 Medium':'#eab308','🟢 Low':'#22c55e'
                          })
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig2, use_container_width=True)

        # Radar chart — risk profile
        st.markdown("### 🕷️ Risk Profile Radar")
        categories = ['Destructive','Intermittent','CDC','Power','Complexity']
        values = [
            df['destructive_risk'].mean(),
            df['intermittent_risk'].mean(),
            df['cdc_risk'].mean(),
            df['power_risk'].mean(),
            df['structural_complexity'].mean()
        ]
        fig_radar = go.Figure(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            fillcolor='rgba(102,126,234,0.3)',
            line=dict(color='#667eea', width=2)
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,1])),
            paper_bgcolor='rgba(0,0,0,0)', font_color='white',
            title="Module Risk Radar"
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── Tab 2: Lint Checker ──────────────────────────────────────────────────
    with tab2:
        st.markdown("### 🪲 RTL Lint Rule Checker — 20 Rules")

        if lint_df.empty:
            st.success("✅ No lint violations found!")
        else:
            # Summary counts
            lc1, lc2, lc3 = st.columns(3)
            errors   = lint_df[lint_df['severity'].str.contains('Error')] if 'severity' in lint_df else pd.DataFrame()
            warnings = lint_df[lint_df['severity'].str.contains('Warning')] if 'severity' in lint_df else pd.DataFrame()
            infos    = lint_df[lint_df['severity'].str.contains('Info')] if 'severity' in lint_df else pd.DataFrame()

            with lc1: st.metric("🔴 Errors",   len(errors))
            with lc2: st.metric("🟠 Warnings", len(warnings))
            with lc3: st.metric("🟡 Info",     len(infos))

            st.markdown("#### Violations")
            lf1, lf2 = st.columns(2)
            with lf1:
                sev_opts = ['All'] + sorted(lint_df['severity'].unique().tolist())
                sev_sel  = st.selectbox("Filter by severity", sev_opts, key="lint_sev")
            with lf2:
                rule_opts = ['All'] + sorted(lint_df['rule_id'].unique().tolist())
                rule_sel  = st.selectbox("Filter by rule ID", rule_opts, key="lint_rule")

            filt_lint = lint_df.copy()
            if sev_sel != 'All':
                filt_lint = filt_lint[filt_lint['severity'] == sev_sel]
            if rule_sel != 'All':
                filt_lint = filt_lint[filt_lint['rule_id'] == rule_sel]
            st.caption(f"{len(filt_lint)} of {len(lint_df)} violations shown")

            for _, row in filt_lint.iterrows():
                sev = row.get('severity','')
                icon = '🔴' if 'Error' in sev else ('🟠' if 'Warning' in sev else '🟡')
                with st.expander(
                    f"{icon} [{row.get('rule_id','')}] Line {row.get('line',0)}: {row.get('message','')}"
                ):
                    st.code(row.get('raw_line',''), language='verilog')
                    st.markdown(f"**🔧 Fix:** {row.get('fix','')}")

            # Lint severity chart
            sev_counts = lint_df['severity'].value_counts().reset_index()
            sev_counts.columns = ['Severity','Count']
            fig_lint = px.bar(sev_counts, x='Severity', y='Count',
                              color='Severity',
                              color_discrete_map={
                                  '🔴 Error':'#ef4444',
                                  '🟠 Warning':'#f97316',
                                  '🟡 Info':'#eab308'
                              },
                              title="Lint Violations by Severity")
            fig_lint.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_lint, use_container_width=True)

    # ── Tab 3: Metrics ───────────────────────────────────────────────────────
    with tab3:
        st.markdown("### � Signal Inventory")
        tc1, tc2 = st.columns(2)
        with tc1:
            type_counts = pd.DataFrame(
                [{'Type': s.signal_type} for s in rtl.signals.values()]
            )['Type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Count']
            fig_types = px.pie(type_counts, names='Type', values='Count',
                               title="Signal Type Distribution",
                               color_discrete_sequence=px.colors.qualitative.Set3)
            fig_types.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_types, use_container_width=True)
        with tc2:
            width_df = pd.DataFrame(
                [{'Signal': n, 'Width': s.width, 'Type': s.signal_type}
                 for n, s in rtl.signals.items()]
            ).sort_values('Width', ascending=False)
            fig_widths = px.bar(width_df.head(20), x='Signal', y='Width',
                                color='Type', title="Signal Bit-Widths (Top 20)",
                                color_discrete_sequence=px.colors.qualitative.Set3)
            fig_widths.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_widths, use_container_width=True)

        st.markdown("### �📊 Signal Metrics Table")
        mcols = ['signal','initial_weight','impact_score','susceptibility',
                 'execution_probability','structural_complexity']
        avail_m = [c for c in mcols if c in df.columns]
        st.dataframe(
            df[avail_m].drop_duplicates('signal').sort_values('impact_score', ascending=False),
            use_container_width=True, height=300
        )

        st.markdown("### 🗺️ Metrics Heatmap")
        heat_df = df[avail_m].copy()
        heat_df = heat_df.drop_duplicates(subset=['signal'])
        heat_df = heat_df.set_index('signal').apply(pd.to_numeric, errors='coerce')
        fig_heat = px.imshow(heat_df.T,
                             color_continuous_scale='RdYlGn_r',
                             title="Metrics Heatmap (Red = High)",
                             aspect='auto')
        fig_heat.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig_heat, use_container_width=True)

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            fig_imp = px.bar(
                df.drop_duplicates('signal').sort_values('impact_score', ascending=False),
                x='signal', y='impact_score', color='impact_score',
                color_continuous_scale='Reds', title="Impact Score per Signal"
            )
            fig_imp.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_imp, use_container_width=True)

        with col_m2:
            fig_sc = px.scatter(
                df, x='impact_score', y='structural_complexity',
                size='overall_risk', color='risk_level',
                hover_data=['signal','raw_line'],
                title="Impact vs Complexity",
                color_discrete_map={
                    '🔴 Critical':'#ef4444','🟠 High':'#f97316',
                    '🟡 Medium':'#eab308','🟢 Low':'#22c55e'
                }
            )
            fig_sc.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_sc, use_container_width=True)

    # ── Tab 4: Waveform ──────────────────────────────────────────────────────
    with tab4:
        st.markdown("### 🌊 Simulated Signal Waveforms")
        st.caption("Synthetic waveforms based on execution probability — shows toggle activity per signal")

        if waveforms:
            # Toggle count bar
            toggle_df = pd.DataFrame([
                {'Signal': s, 'Toggles': t, 'Activity': 'High' if t > 10 else ('Medium' if t > 5 else 'Low')}
                for s, t in sorted(toggles.items(), key=lambda x: x[1], reverse=True)
            ])

            fig_tog = px.bar(
                toggle_df, x='Signal', y='Toggles',
                color='Activity',
                color_discrete_map={'High':'#ef4444','Medium':'#f97316','Low':'#22c55e'},
                title=f"Signal Toggle Count over {waveform_cycles} cycles (High toggles = High power)"
            )
            fig_tog.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_tog, use_container_width=True)

            # Waveform display
            st.markdown("#### Digital Waveform View")
            cycles = list(range(waveform_cycles))
            signals_to_show = list(waveforms.keys())[:8]

            fig_wave = go.Figure()
            for idx, sig in enumerate(signals_to_show):
                wave = waveforms[sig][:waveform_cycles]
                # Offset each signal vertically
                offset = idx * 2
                y_vals = [v + offset for v in wave]
                fig_wave.add_trace(go.Scatter(
                    x=cycles, y=y_vals,
                    mode='lines',
                    name=sig,
                    line=dict(width=2, shape='hv'),
                ))

            fig_wave.update_layout(
                title="Digital Waveform Simulation",
                xaxis_title="Clock Cycle",
                yaxis=dict(
                    tickvals=[i*2+0.5 for i in range(len(signals_to_show))],
                    ticktext=signals_to_show,
                    showgrid=False
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,30,46,0.8)',
                font_color='white',
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_wave, use_container_width=True)

    # ── Tab 5: Dependency Graph ───────────────────────────────────────────────
    with tab5:
        st.markdown("### 🕸️ Signal Dependency Graph")
        G = graph.graph
        if G.nodes:
            pos = nx.spring_layout(G, seed=42, k=2)

            edge_x, edge_y = [], []
            for u, v in G.edges():
                x0,y0 = pos[u]; x1,y1 = pos[v]
                edge_x += [x0,x1,None]; edge_y += [y0,y1,None]

            def node_color(n):
                s = rtl.signals.get(n)
                if not s: return '#888'
                if 'output' in s.signal_type: return '#ef4444'
                if 'input'  in s.signal_type: return '#22c55e'
                return '#667eea'

            node_trace = go.Scatter(
                x=[pos[n][0] for n in G.nodes],
                y=[pos[n][1] for n in G.nodes],
                mode='markers+text',
                text=list(G.nodes),
                textposition='top center',
                marker=dict(
                    size=20,
                    color=[node_color(n) for n in G.nodes],
                    line=dict(width=2, color='white')
                )
            )
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y, mode='lines',
                line=dict(width=1.5, color='#667eea'),
                hoverinfo='none'
            )
            fig_g = go.Figure(
                data=[edge_trace, node_trace],
                layout=go.Layout(
                    title='Signal Dependency Graph  |  🟢 Input  🔴 Output  🔵 Internal',
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
                    yaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
                    margin=dict(l=20,r=20,t=60,b=20),
                    height=500
                )
            )
            st.plotly_chart(fig_g, use_container_width=True)

        st.markdown("### 🔗 Critical Signal Paths")
        critical = graph.get_critical_nodes()[:10]
        if critical:
            st.dataframe(
                pd.DataFrame(critical, columns=['Signal','Centrality']),
                use_container_width=True
            )

    # ── Tab 6: CDC ───────────────────────────────────────────────────────────
    with tab6:
        st.markdown("### ⚡ Clock Domain Crossing (CDC) Analysis")
        cdc_df = df[df['has_cdc_issue'] == True] if 'has_cdc_issue' in df.columns else pd.DataFrame()

        cc1, cc2, cc3 = st.columns(3)
        with cc1: st.metric("🕐 Clock Domains", max(len(rtl.clock_signals),1))
        with cc2: st.metric("⚠️ CDC Operations", len(cdc_df))
        with cc3: st.metric("🔧 Reset Signals",  len(rtl.reset_signals))

        if rtl.clock_signals:
            st.success(f"✅ Clocks detected: **{', '.join(rtl.clock_signals)}**")
        else:
            st.warning("⚠️ No explicit clock signals found.")

        if not cdc_df.empty:
            cdc_disp = [c for c in ['line','signal','raw_line','cdc_risk','susceptibility']
                        if c in cdc_df.columns]
            st.dataframe(cdc_df[cdc_disp].sort_values('cdc_risk',ascending=False),
                         use_container_width=True)
            fig_cdc = px.bar(cdc_df, x='signal', y='cdc_risk',
                             color='cdc_risk', color_continuous_scale='Reds',
                             title="CDC Risk by Signal")
            fig_cdc.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_cdc, use_container_width=True)

    # ── Tab 7: Fix Suggestions ───────────────────────────────────────────────
    with tab7:
        st.markdown("### 💡 AI-Powered Fix Suggestions")

        top10 = df.sort_values('overall_risk', ascending=False).head(10)
        for _, row in top10.iterrows():
            icon = {'🔴 Critical':'🚨','🟠 High':'⚠️','🟡 Medium':'💛','🟢 Low':'✅'}.get(row['risk_level'],'❓')
            with st.expander(
                f"{icon} Line {row['line']}: `{row['raw_line'][:55]}` — {row['risk_level']} ({row['overall_risk']:.3f})"
            ):
                fc1, fc2 = st.columns(2)
                with fc1:
                    st.markdown(f"**Signal:** `{row['signal']}`")
                    st.markdown(f"**Operator:** `{row['operator']}`")
                    st.markdown(f"**Exec Probability:** `{row['execution_probability']}`")
                    st.markdown(f"**Toggles (power):** `{toggles.get(row['signal'],0)}`")
                with fc2:
                    st.markdown(f"**💥 Destructive:** `{row['destructive_risk']:.3f}`")
                    st.markdown(f"**🎲 Intermittent:** `{row['intermittent_risk']:.3f}`")
                    st.markdown(f"**⚡ CDC Risk:** `{row['cdc_risk']:.3f}`")
                    st.markdown(f"**🔋 Power Risk:** `{row['power_risk']:.3f}`")
                st.divider()
                st.markdown("**🔧 Recommended Fixes:**")
                for fix in row['fix_suggestion'].split(' | '):
                    st.markdown(f"- {fix}")
        # Export
        st.divider()
        st.markdown("### 📥 Export Full Report")
        ec1, ec2, ec3 = st.columns(3)

        with ec1:
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ Download Risk CSV", csv,
                "rtl_risk_report.csv", "text/csv",
                use_container_width=True
            )
        with ec2:
            if not lint_df.empty:
                lint_csv = lint_df.to_csv(index=False)
                st.download_button(
                    "⬇️ Download Lint CSV", lint_csv,
                    "rtl_lint_report.csv", "text/csv",
                    use_container_width=True
                )
        with ec3:
            try:
                from analyzer.pdf_report import generate_pdf_report
                pdf_bytes = generate_pdf_report(
                    module_name=rtl.module_name,
                    health=health,
                    records=records,
                    lint_violations=lint_violations,
                    rtl_signals=rtl.signals,
                    toggles=toggles
                )
                st.download_button(
                    "📄 Download PDF Report", pdf_bytes,
                    f"{rtl.module_name}_rtl_report.pdf",
                    "application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF error: {e}")

else:
    # Landing page
    st.markdown("""
    <div style="text-align:center;padding:60px 20px">
      <div style="font-size:5rem">⚡</div>
      <h2>RTL Insight Engine v2.0</h2>
      <p style="color:#888;font-size:1.1rem;max-width:600px;margin:auto">
        Upload a Verilog (.v) or SystemVerilog (.sv) file,<br>
        or choose a demo from the sidebar.
      </p>
    </div>
    """, unsafe_allow_html=True)

    l1,l2,l3,l4,l5 = st.columns(5)
    with l1: st.info("**⚡ Lint**\n20 rule checks")
    with l2: st.info("**🔄 CDC**\nClock crossing")
    with l3: st.info("**🔋 Power**\nToggle analysis")
    with l4: st.info("**🌊 Waveform**\nSignal simulation")
    with l5: st.info("**📊 Metrics**\n5-metric engine")