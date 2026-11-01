#!/usr/bin/env python3
"""Escenarios de asignación de ahorro nuevo. Input JSON:
{"neto":667635,"bruto":1127671,"caucion":460035,"ar_soberano":716549,"ar_ytm":13.59,"tasa_caucion":0.5,
 "tasa_libre_riesgo":4.1,"flujo":130000,"shock_ar_pct":10}
Escenarios: A repagar caución | B diversificar fuera de AR | C mixto 50/50 | D más AO29/soberano AR (solo referencia).
Salida por escenario: neto, apalancamiento, % AR sobre neto, pérdida por shock AR (USD y % neto) y delta de carry anual vs. no hacer nada."""
import json, sys

def esc(s, name, repago, div, ar):
    caucion = s["caucion"] - repago
    bruto = s["bruto"] + div + ar          # el repago usa caja ya existente: no cambia el bruto
    neto = bruto - caucion
    arv = s["ar_soberano"] + ar
    shock = arv * s["shock_ar_pct"] / 100
    carry = repago * s["tasa_caucion"] / 100 + div * s["tasa_libre_riesgo"] / 100 + ar * s["ar_ytm"] / 100
    return {"escenario": name, "repago_caucion": round(repago), "a_activos_no_AR": round(div), "a_soberano_AR": round(ar),
            "neto": round(neto), "bruto": round(bruto), "caucion": round(caucion),
            "apalancamiento": round(bruto / neto, 2), "ar_pct_neto": round(100 * arv / neto, 1),
            "perdida_shock_ar_usd": round(shock), "perdida_shock_ar_pct_neto": round(100 * shock / neto, 1),
            "delta_carry_anual_usd": round(carry)}

def main():
    s = json.load(open(sys.argv[1])); f = s["flujo"]
    base = esc(s, "Base (sin ahorro nuevo)", 0, 0, 0); base["neto"] = round(s["neto"])
    out = [base,
           esc({**s, "bruto": s["bruto"], "neto": s["neto"]}, "A. Repagar caución", f, 0, 0),
           esc(s, "B. Diversificar fuera de AR", 0, f, 0),
           esc(s, "C. Mixto 50/50", f / 2, f / 2, 0),
           esc(s, "D. Más soberano AR (referencia)", 0, 0, f)]
    # el ahorro suma al neto en A (por menor deuda) y en B/D (por más activos); base sin flujo
    base.update({"apalancamiento": round(s["bruto"] / s["neto"], 2), "ar_pct_neto": round(100 * s["ar_soberano"] / s["neto"], 1),
                 "perdida_shock_ar_usd": round(s["ar_soberano"] * s["shock_ar_pct"] / 100),
                 "perdida_shock_ar_pct_neto": round(100 * s["ar_soberano"] * s["shock_ar_pct"] / 100 / s["neto"], 1),
                 "delta_carry_anual_usd": 0, "bruto": round(s["bruto"]), "caucion": round(s["caucion"])})
    print(json.dumps(out, indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main()
