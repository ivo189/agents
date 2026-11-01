#!/usr/bin/env python3
"""Proyección de volumen. Input JSON: {"TICKER": [vol_diario_mas_viejo, ..., vol_ultimo_dia], ...}
(mínimo 21 ruedas por ticker). Uso: python volume_projection.py input.json [--event TICKER=YYYY-MM-DD ...]
Método: base = mediana 20d (robusta a picos); proyección próxima rueda = 0.6*base + 0.4*EWMA(5d);
banda = base ± 1 desvío (MAD escalado) de los últimos 20d. Cerca de un evento (observación de nota,
rebalanceo) se marca 'evento' pero NO se ajusta el número: es un aviso, no un modelo."""
import json, sys, statistics as st

def ewma(xs, n):
    a = 2 / (n + 1); e = xs[0]
    for x in xs[1:]: e = a * x + (1 - a) * e
    return e

def main():
    data = json.load(open(sys.argv[1]))
    events = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a and not a.startswith("-"))
    out = {}
    for t, v in data.items():
        if len(v) < 21:
            out[t] = {"error": f"solo {len(v)} ruedas, hacen falta 21"}; continue
        w = v[-21:-1]; last = v[-1]
        med = st.median(w); mad = st.median([abs(x - med) for x in w]) * 1.4826
        proj = 0.6 * med + 0.4 * ewma(v[-5:], 5)
        out[t] = {"ultimo": last, "mediana20d": med, "ratio_vs_mediana": round(last / med, 2) if med else None,
                  "proyeccion_proxima_rueda": round(proj), "banda": [round(max(proj - mad, 0)), round(proj + mad)],
                  "evento": events.get(t)}
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
