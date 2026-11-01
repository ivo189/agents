#!/usr/bin/env python3
"""Métricas de la curva soberana. Input JSON: {"fecha":"YYYY-MM-DD","riesgo_pais":int|null,
"bonos":[{"ticker":"GD30","vencimiento":"2030-07-09","tir":10.2,"duration":3.1,"paridad":78.5,"precio":..,"var_dia":..}]}
Imprime: curva ordenada, pendiente (último-primero y tramo 30→35→41), butterfly, y ranking de tramos
más empinados. TIR en % anual USD. Si se pasa --prev prev.json, agrega cambios en pb por bono."""
import json, sys

def main():
    cur = json.load(open(sys.argv[1]))
    prev = None
    if "--prev" in sys.argv: prev = json.load(open(sys.argv[sys.argv.index("--prev") + 1]))
    pb = {b["ticker"]: b["tir"] for b in prev["bonos"]} if prev else {}
    bs = sorted([b for b in cur["bonos"] if b.get("tir") is not None], key=lambda b: b["vencimiento"])
    rows = []
    for b in bs:
        rows.append({**b, "cambio_pb": round((b["tir"] - pb[b["ticker"]]) * 100) if b["ticker"] in pb else None})
    seg = [{"tramo": f'{a["ticker"]}→{b["ticker"]}', "pb": round((b["tir"] - a["tir"]) * 100)} for a, b in zip(bs, bs[1:])]
    res = {"fecha": cur.get("fecha"), "riesgo_pais": cur.get("riesgo_pais"), "curva": rows, "tramos": seg}
    if len(bs) >= 2:
        res["pendiente_total_pb"] = round((bs[-1]["tir"] - bs[0]["tir"]) * 100)
        res["invertida"] = any(s["pb"] < 0 for s in seg)
    if len(bs) >= 3:
        m = len(bs) // 2
        res["butterfly_pb"] = round((2 * bs[m]["tir"] - bs[0]["tir"] - bs[-1]["tir"]) * 100)
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
