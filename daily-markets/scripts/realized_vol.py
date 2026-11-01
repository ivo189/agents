#!/usr/bin/env python3
"""Volatilidad realizada anualizada 20d y 60d. Input JSON: {"TICKER": [cierre_viejo, ..., cierre_ultimo], ...} (>=61 cierres).
Salida: vol20, vol60 (%), ratio 20/60 y señal ('subiendo' si ratio>1.2, 'bajando' si <0.8)."""
import json, sys, math, statistics as st

def vol(cs, n):
    r = [math.log(b / a) for a, b in zip(cs[-n-1:-1], cs[-n:])]
    return st.stdev(r) * math.sqrt(252) * 100

out = {}
for t, cs in json.load(open(sys.argv[1])).items():
    if len(cs) < 61 or min(cs) <= 0:
        out[t] = {"error": "datos insuficientes o inválidos (se necesitan 61 cierres > 0)"}; continue
    v20, v60 = vol(cs, 20), vol(cs, 60); r = v20 / v60
    out[t] = {"vol20": round(v20, 1), "vol60": round(v60, 1), "ratio": round(r, 2),
              "senal": "subiendo" if r > 1.2 else "bajando" if r < 0.8 else "estable"}
print(json.dumps(out, indent=2, ensure_ascii=False))
