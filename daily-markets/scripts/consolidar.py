#!/usr/bin/env python3
"""Consolida el patrimonio de todas las fuentes. Input JSON:
{"fecha":"YYYY-MM-DD","fx":{"ARS_MEP":1567.43,"MXN":17.9},   # unidades de moneda por 1 USD
 "posiciones":[{"fuente":"Cocos","cuenta":"...","activo":"AO29","clase":"bono_soberano_ar|nota_estructurada|accion|fondo|cash|otro",
   "moneda":"USD|ARS|MXN|EUR","valor":123.4,"valor_usd":null,"expo":{"MELI":0.5,"NU":0.5}}],   # expo: fracción del valor por subyacente (opcional)
 "pasivos":[{"fuente":"Cocos","concepto":"caucion","moneda":"ARS","valor":721073208.65}],
 "antiguedad_dias":{"Cocos":1,"Citi":9}}
Si valor_usd es null se convierte con fx (USD=1; EUR requiere fx.EUR como USD por EUR -> poner 'EUR_USD'). Salida: totales USD
(bruto, pasivos, neto), % por fuente/clase/moneda, top 10, exposición por subyacente y alertas de datos viejos (>10 días)."""
import json, sys
from collections import defaultdict

def usd(v, mon, fx):
    if mon == "USD": return v
    if mon == "ARS": return v / fx["ARS_MEP"]
    if mon == "MXN": return v / fx["MXN"]
    if mon == "EUR": return v * fx["EUR_USD"]
    raise ValueError(f"sin FX para {mon}")

def main():
    d = json.load(open(sys.argv[1])); fx = d.get("fx", {})
    P = []
    for p in d["posiciones"]:
        u = p.get("valor_usd") if p.get("valor_usd") is not None else usd(p["valor"], p["moneda"], fx)
        P.append({**p, "usd": u})
    L = sum(usd(l["valor"], l["moneda"], fx) for l in d.get("pasivos", []))
    bruto = sum(p["usd"] for p in P); neto = bruto - L
    def agg(k):
        a = defaultdict(float)
        for p in P: a[p[k]] += p["usd"]
        return {x: {"usd": round(v), "pct_bruto": round(100 * v / bruto, 1)} for x, v in sorted(a.items(), key=lambda t: -t[1])}
    expo = defaultdict(float)
    for p in P:
        for t, f in (p.get("expo") or {}).items(): expo[t] += p["usd"] * f
    old = {k: v for k, v in d.get("antiguedad_dias", {}).items() if v > 10}
    print(json.dumps({"fecha": d.get("fecha"), "bruto_usd": round(bruto), "pasivos_usd": round(L), "neto_usd": round(neto),
        "apalancamiento_bruto_neto": round(bruto / neto, 2) if neto > 0 else None,
        "por_fuente": agg("fuente"), "por_clase": agg("clase"), "por_moneda": agg("moneda"),
        "top10": [{"activo": p["activo"], "fuente": p["fuente"], "usd": round(p["usd"]), "pct_bruto": round(100 * p["usd"] / bruto, 1)}
                  for p in sorted(P, key=lambda p: -p["usd"])[:10]],
        "exposicion_subyacente_usd": {t: {"usd": round(v), "pct_neto": round(100 * v / neto, 1) if neto > 0 else None}
                                      for t, v in sorted(expo.items(), key=lambda t: -t[1])},
        "datos_viejos_mas_de_10_dias": old}, indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main()
