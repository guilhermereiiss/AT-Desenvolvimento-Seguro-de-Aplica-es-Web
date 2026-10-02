"""Security gate do ZAP: falha (exit 1) se houver alerta High (riskcode 3). Uso: python scripts/zap_gate.py zap.json"""
import json
import sys

dados = json.load(open(sys.argv[1]))
altos = [a for site in dados.get("site", []) for a in site.get("alerts", []) if int(a.get("riskcode", 0)) >= 3]
for a in altos:
    print(f"[HIGH] {a.get('name')}")
print(f"ZAP gate: {len(altos)} alerta(s) High")
sys.exit(1 if altos else 0)
