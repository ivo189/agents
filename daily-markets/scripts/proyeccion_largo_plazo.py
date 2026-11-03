#!/usr/bin/env python3
"""Plan a largo plazo v2: 3 escenarios de riesgo pais x estrategias, mensual nov-2026 .. oct-2029 (vence AO29).
Estrategias:
  A  : todo flujo (aportes + cupones + vencimientos) repaga caucion en Cocos hasta cerrarla; luego T-bills.
  A2 : mitad del aporte fresco repaga caucion y mitad va a un fondo USA 60/40; TODOS los cupones/vencimientos repagan caucion.
  A4 : como A2, pero ademas vende hoy los bonos largos (AL35, AE38, AL41, GD46, GD29) y usa el producto para repagar caucion.
  B  : todo flujo a T-bills afuera; la caucion se mantiene y solo se cancela al vencer el AO29 (colateral).
Uso: python proyeccion_largo_plazo.py [--json] [--recovery -1|0.40] [--ret-otros 6] [--caucion-tasa 0.5] [--tbill 4.1]
     [--ret-acc 7] [--ret-rf 4.5] [--eq-shock-dic27 0]
Cupones: AO29 mensual 0,5%; resto semestral (ene/jul); notas de Cocos (70.000 en 3 notas) segun term sheets, capital al par a vencimiento."""
import json, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--recovery", type=float, default=-1)         # -1 = precio implicito en el riesgo pais del escenario; 0.40 = estres
ap.add_argument("--ret-otros", type=float, default=6.0)       # retorno anual esperado de lo que no es Cocos (Citi, HSBC, IBKR); 6% = igual al 60/40
ap.add_argument("--caucion-tasa", type=float, default=0.5)
ap.add_argument("--tbill", type=float, default=4.1)
ap.add_argument("--ret-acc", type=float, default=7.0)         # retorno esperado renta variable USA (anual %)
ap.add_argument("--ret-rf", type=float, default=4.5)          # retorno esperado renta fija USA (anual %)
ap.add_argument("--eq-shock-dic27", type=float, default=0.0)  # shock de renta variable en dic-2027 (p.ej. -0.25)
ap.add_argument("--election-m", type=int, default=12)
ap.add_argument("--pre-path", default="0:795.7,11:795.7")    # riesgo pais previo a la eleccion: anclas "mes:pb" (interpolacion lineal), comun a los 3 escenarios
ap.add_argument("--s2-peak", type=float, default=1600)   # S2: riesgo pais tras la eleccion (shock)
ap.add_argument("--s2-hold", type=int, default=6)        # S2: meses que se mantiene el pico
ap.add_argument("--s2-end", type=float, default=900)     # S2: riesgo pais a oct-2029 (normalizacion lineal desde el pico)
ap.add_argument("--json", action="store_true")
args = ap.parse_args()

RP0 = 795.7
UST = lambda T: 4.6 if T <= 3.5 else 4.9
BONOS = {"AO29": (560480, 81.95, 13.76, 2.54, 911), "AL35": (67503, 66.29, 12.74, 4.86, 797), "AE38": (66877, 68.86, 13.38, 3.93, 863),
         "AL41": (16636, 61.30, 12.78, 5.06, 794), "GD46": (4841, 59.89, 11.29, 5.54, 635), "GD29": (213, 54.85, 7.51, 1.33, 306)}
LARGOS = ["AL35", "AE38", "AL41", "GD46", "GD29"]
CAUCION0 = 460035
NO_COCOS = 1127671 - 797457
CASH_COCOS = 9798            # Cocos: efectivo/FCI remanente (el cable USD 30 mil financia la nota de 30 mil, supuesto)
NOTAS = [("MSFT/ORCL", 10000, lambda m: 79 if 1 <= m <= 19 else 0, 19),
         ("MELI/NU", 30000, lambda m: 300 if 1 <= m <= 21 else 0, 21),
         ("BBD/MELI/NU", 30000, lambda m: 1500 if 5 <= m <= 26 and (m - 5) % 3 == 0 else 0, 26)]
DEFAULT_M = 14

def price(y, c, T):
    if T <= 0: return 100.0
    y /= 100; v = (1 + y / 2) ** (-2 * T)
    return c / 100 * (1 - v) / y * 100 + 100 * v
def mdur(y, c, T, h=0.01): return -(price(y + h, c, T) - price(y - h, c, T)) / (2 * h) / price(y, c, T) * 100
def yield_implicito(P0, c, T):
    lo, hi = 0.5, 80.0
    for _ in range(80):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if price(mid, c, T) > P0 else (lo, mid)
    return (lo + hi) / 2
def calibrar(P0, y0, D0):
    lo, hi = 0.3, 25.0
    def c_de(T):
        y = y0 / 100; v = (1 + y / 2) ** (-2 * T); return (P0 / 100 - v) / ((1 - v) / y) * 100
    for _ in range(80):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if mdur(y0, max(c_de(mid), 0), mid) - D0 < 0 else (lo, mid)
    T = (lo + hi) / 2
    return max(c_de(T), 0), T

POS = {}
for k, (val, P0, y0, D0, g) in BONOS.items():
    if k == "AO29":
        c, T0 = 6.0, 3.0; g = (yield_implicito(P0, c, T0) - UST(T0)) * 100
    else: c, T0 = calibrar(P0, y0, D0)
    POS[k] = {"face": val / (P0 / 100), "c": c, "T0": T0, "g": g}

def ahorro(m):
    t = 10 + m; yy, mm = 2026 + (t - 1) // 12, (t - 1) % 12 + 1
    f = {(2026, 11): 15000, (2026, 12): 15000, (2027, 1): 80000, (2027, 2): 20000, (2027, 3): 20000}
    if (yy, mm) in f: return f[(yy, mm)]
    if yy == 2027 and 4 <= mm <= 12: return 6000
    if yy == 2028 and mm == 1: return 100000
    if (yy == 2028 and mm >= 2) or (yy == 2029 and mm <= 10): return 3000
    return 0
def fecha(m):
    t = 10 + m; return f"{2026 + (t - 1) // 12}-{(t - 1) % 12 + 1:02d}"

def escenarios():
    e = args.election_m
    return {"S1": {"nombre": "Milei reelecto (RP 300)", "post": [(e, 300)], "default": False},
            "S2": {"nombre": f"Oposición que paga, shock post-elección (RP {int(args.s2_peak)})", "post": [(e, args.s2_peak), (e + args.s2_hold, args.s2_peak), (36, args.s2_end)], "default": False},
            "S3": {"nombre": "Reestructuración / canje (RP 2000)", "post": [(e, 2000)], "default": True}}
ESTRATEGIAS = ["A", "A2", "A4", "B"]
r_fund = ((0.6 * (1 + args.ret_acc / 100) + 0.4 * (1 + args.ret_rf / 100))) ** (1 / 12) - 1   # 60/40 rebalanceado mensual aprox.

def _anclas():
    pts = sorted((int(a.split(":")[0]), float(a.split(":")[1])) for a in args.pre_path.split(","))
    return pts
PRE = _anclas()
def rp_pre(m):
    if m <= PRE[0][0]: return PRE[0][1]
    for (m0, r0), (m1, r1) in zip(PRE, PRE[1:]):
        if m <= m1: return r0 + (r1 - r0) * (m - m0) / (m1 - m0)
    return PRE[-1][1]
def rp_path(rp): return [round(rp_pre(m) if m < args.election_m else rp, 1) for m in range(37)]

def rp_t(m, scn):
    if m < args.election_m: return rp_pre(m)
    pts = scn["post"]
    if m <= pts[0][0]: return pts[0][1]
    for (m0, r0), (m1, r1) in zip(pts, pts[1:]):
        if m <= m1: return r0 + (r1 - r0) * (m - m0) / (m1 - m0) if m1 > m0 else r1
    return pts[-1][1]

def valor_bono(k, m, scn, defaulted):
    p = POS[k]; T = p["T0"] - m / 12
    if defaulted:
        if args.recovery < 0:
            T14 = p["T0"] - DEFAULT_M / 12
            px = price(UST(max(T14, 0.01)) + rp_t(DEFAULT_M, scn) * p["g"] / RP0 / 100, p["c"], T14)
        else: px = args.recovery * 100
    else:
        px = price(UST(max(T, 0.01)) + rp_t(m, scn) * p["g"] / RP0 / 100, p["c"], T) if T > 0 else 100.0
    return p["face"] * px / 100

def correr(scn, est):
    caucion, tbills, fund = CAUCION0, 0.0, 0.0
    no_cocos = NO_COCOS; vendidos = set(); rows = []
    for m in range(0, 37):
        defaulted = scn["default"] and m >= DEFAULT_M
        if m > 0: no_cocos *= (1 + args.ret_otros / 100) ** (1 / 12)
        ar = 0.0; cup = 0.0; venc = 0.0; venta = 0.0; venc_ao = 0.0
        for k, p in POS.items():
            if k in vendidos: continue
            val = valor_bono(k, m, scn, defaulted)
            if est == "A4" and m == 1 and k in LARGOS:
                venta += val; vendidos.add(k); continue
            if m > 0 and not defaulted:
                if k == "AO29": cup += p["face"] * 0.005
                elif m % 6 == 3: cup += p["face"] * p["c"] / 100 / 2
            if k == "AO29" and m == 36 and not defaulted: venc += val; venc_ao += val; val = 0.0
            ar += val
        notas = 0.0
        for nombre, monto, cf, vm in NOTAS:
            if m < vm: notas += monto
            if m > 0: cup += cf(m)
            if m == vm: venc += monto
        if m > 0:
            if est in ("A2", "A4") and m == args.election_m + 2 and args.eq_shock_dic27: fund *= (1 + 0.6 * args.eq_shock_dic27)
            tbills *= (1 + args.tbill / 100 / 12); fund *= (1 + r_fund)
            flujo = cup + venc + venta - caucion * args.caucion_tasa / 100 / 12
            fresco = ahorro(m)
            if est == "A":
                rep = min(flujo + fresco, caucion); caucion -= rep; tbills += flujo + fresco - rep
            elif est in ("A2", "A4"):
                pool = flujo + fresco / 2; rep = min(pool, caucion); caucion -= rep; fund += fresco / 2 + (pool - rep)
            else:
                rep = min(venc_ao, caucion) if venc_ao else 0.0; caucion -= rep; tbills += flujo + fresco - rep
        cocos_gross = ar + notas + CASH_COCOS
        gross = cocos_gross + no_cocos + tbills + fund
        neto = gross - caucion; cn = cocos_gross - caucion
        rows.append({"m": m, "fecha": fecha(m) if m else "2026-10", "ar": round(ar), "notas": round(notas), "caucion": round(caucion),
                     "tbills": round(tbills), "fondo_6040": round(fund), "bruto": round(gross), "neto": round(neto),
                     "lev_global": round(gross / neto, 2) if neto > 0 else None, "cocos_neto": round(cn),
                     "lev_cocos": round(cocos_gross / cn, 2) if cn > 0 else None,
                     "ar_pct_neto": round(100 * ar / neto, 1) if neto > 0 else None})
    return rows

def todo():
    out = {"aportes_usd": [{"m": m, "fecha": fecha(m), "monto": ahorro(m)} for m in range(1, 37)],
           "parametros": {k: v for k, v in vars(args).items() if k != "json"},
           "calibracion": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in POS.items()}, "resultados": {}}
    for s, scn in escenarios().items():
        out["resultados"][s] = {"nombre": scn["nombre"], "rp_path": [round(rp_t(m, scn), 1) for m in range(37)],
                                "estrategias": {e: correr(scn, e) for e in ESTRATEGIAS}}
    return out

if __name__ == "__main__":
    out = todo()
    if args.json: print(json.dumps(out, ensure_ascii=False))
    else:
        for s, v in out["resultados"].items():
            for e, rows in v["estrategias"].items():
                print(s, v["nombre"], e)
                for r in rows:
                    if r["m"] in (0, 5, 12, 14, 26, 36):
                        print("  ", r["fecha"], {k: r[k] for k in ("ar", "caucion", "fondo_6040", "tbills", "neto", "lev_global", "lev_cocos", "ar_pct_neto")})
