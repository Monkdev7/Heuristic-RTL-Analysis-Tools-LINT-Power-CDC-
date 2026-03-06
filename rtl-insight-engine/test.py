from analyzer import analyze_rtl

rtl, graph, records, health = analyze_rtl('samples/alu.v')

print(f"Module: {rtl.module_name}")
print(f"Signals found: {list(rtl.signals.keys())}")
print(f"Operations found: {len(records)}")
print(f"\n🏥 RTL Health Score: {health['score']} / 100  {health['grade']}")
print(f"\n🎯 Top 5 Risks:")
for r in sorted(records, key=lambda x: x['overall_risk'], reverse=True)[:5]:
    print(f"  {r['risk_level']} | Line {r['line']}: {r['raw_line']}")