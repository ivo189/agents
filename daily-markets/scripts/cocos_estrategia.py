#!/usr/bin/env python3
"""Estrategia Cocos con dos objetivos: (1) bajar la caución para ganar capacidad de compra futura; (2) bajar la dependencia de bonos AR en la cartera total.
Precios de BondTerminal 6-nov-2026 (MEP), canje cable->MEP con captura neta del 5,5% (sin comisión), no-Cocos con 6% anual.
Estrategias (mensual nov-26 a dic-27, aportes de Ivo a fin de mes):
  E1 'Repagar todo'          : aportes (canjeados) y cupones repagan caución hasta cerrarla.
  E2 'Repagar y diversificar': igual, pero cuando Cocos baja de 1,8x, los aportes nuevos van a activos no-AR (60/40 en Citi); cupones siguen repagando.
  E3 'Vender largos + repagar': vende hoy los bonos largos (AL35/AE38/AL41/GD46/GD29) y repaga caución; luego como E1.
  E4 'Vender largos + diversificar': como E3 pero diversificando desde 1,8x (como E2).
Métricas: apalancamiento de Cocos; capacidad de compra adicional a 2,0x (L*·neto − activos de Cocos); peso AR en activos totales; pérdida del neto total ante +300 pb de riesgo país."""
import json, argparse
ap = argparse.ArgumentParser(); ap.add_argument("--gap", type=float, default=5.5); ap.add_argument("--ret", type=float, default=6.0); ap.add_argument("--umbral", type=float, default=1.8); ap.add_argument("--json", action="store_true")
a, _ = ap.parse_known_args()
POS = {"AO29": (682075, 76.68, 2.47), "AL35": (99911, 62.31, 4.75), "AE38": (94310, 65.19, 3.78), "AL41": (26543, 58.21, 4.89), "GD46": (7760, 57.73, 5.36), "GD29": (385, 52.81, 1.27)}
VAL = {k: n * p / 100 for k, (n, p, d) in POS.items()}; DUR = {k: v[2] for k, v in POS.items()}
LARGOS = ("AL35", "AE38", "AL41", "GD46", "GD29")
NOTAS, OTROS, CAUC0, NOCOCOS0 = 70000, 9798, 460035, 330214
def aporte(m): return 15000 if m in (1, 2) else 80000 if m == 3 else 20000 if m in (4, 5) else 6000 if 6 <= m <= 14 else 0
LAB = ["oct-26", "nov-26", "dic-26", "ene-27", "feb-27", "mar-27", "abr-27", "may-27", "jun-27", "jul-27", "ago-27", "sep-27", "oct-27", "nov-27", "dic-27"]
def cupones(m, largos):
    c = 682075 * 0.005 + 79 * (m <= 19) + 300 * (m <= 21) + (1500 if m >= 5 and (m - 5) % 3 == 0 else 0)
    if largos and m % 6 == 3: c += 5000
    return c
def correr(vende_largos, diversifica, umbral=None):
    umbral = a.umbral if umbral is None else umbral
    val = dict(VAL); caucion = CAUC0; noc = float(NOCOCOS0); rows = []
    def metricas(m):
        ar = sum(val.values()); G = ar + NOTAS + OTROS; N = G - caucion
        dv = sum(val[k] * DUR[k] for k in val) * 0.03             # pérdida por +300 pb (lineal por duration)
        total = G + noc; neto_t = total - caucion
        return {"m": m, "fecha": LAB[m], "ar": round(ar), "caucion": round(caucion), "noc": round(noc), "lev_cocos": round(G / N, 2) if N > 0 else None,
                "firepower_2x": round(max(2.0 * N - G, 0)), "ar_pct_total": round(100 * ar / total, 1), "ar_pct_neto": round(100 * ar / neto_t, 1),
                "neto_total": round(neto_t), "perdida_300_pct_neto": round(100 * dv / neto_t, 1)}
    rows.append(metricas(0))
    for m in range(1, 15):
        noc *= 1 + a.ret / 100 / 12
        if m == 1 and vende_largos:
            prod = sum(val[k] for k in LARGOS); caucion -= min(prod, caucion)
            for k in LARGOS: val[k] = 0.0
        G = sum(val.values()) + NOTAS + OTROS; N = G - caucion; lev = G / N if N > 0 else 99
        flujo = cupones(m, not vende_largos) - caucion * 0.005 / 12
        rep = min(flujo, caucion); caucion -= rep; noc += flujo - rep
        if diversifica and lev <= umbral: noc += aporte(m)                       # va a activos no-AR, sin canje
        else:
            x = aporte(m) * (1 + a.gap / 100); rep = min(x, caucion); caucion -= rep; noc += x - rep
        rows.append(metricas(m))
    return rows
ESTR = {"E1": ("Repagar todo", correr(False, False)), "E2": ("Repagar y diversificar", correr(False, True)),
        "E3": ("Vender largos + repagar", correr(True, False)), "E4": ("Vender largos + diversificar", correr(True, True))}
def hito(rows, L):
    return next((r["fecha"] for r in rows if r["lev_cocos"] is not None and r["lev_cocos"] <= L), "no llega")
out = {"parametros": {"gap": a.gap, "ret_no_cocos": a.ret, "umbral_diversificar": a.umbral},
       "estrategias": {k: {"nombre": v[0], "filas": v[1], "hito_2_0": hito(v[1], 2.0), "hito_1_8": hito(v[1], 1.8), "hito_1_5": hito(v[1], 1.5)} for k, v in ESTR.items()},
       "largos_usd": round(sum(VAL[k] for k in LARGOS)), "ar_usd": round(sum(VAL.values())), "dv01_largos_pct": round(100 * sum(VAL[k] * DUR[k] for k in LARGOS) / sum(VAL[k] * DUR[k] for k in VAL), 1)}
def run(): return out
if __name__ == "__main__":
    if a.json: print(json.dumps(out, ensure_ascii=False))
    else:
        print({k: out[k] for k in ("largos_usd", "ar_usd", "dv01_largos_pct")})
        for k, v in out["estrategias"].items():
            print(k, v["nombre"], "| 2,0x:", v["hito_2_0"], "1,8x:", v["hito_1_8"], "1,5x:", v["hito_1_5"])
            for r in v["filas"]:
                if r["m"] in (0, 3, 5, 8, 12, 14): print("  ", r["fecha"], {kk: r[kk] for kk in ("lev_cocos", "firepower_2x", "ar_pct_total", "ar_pct_neto", "caucion", "noc", "perdida_300_pct_neto")})
