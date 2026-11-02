#!/usr/bin/env python3
"""Plan a largo plazo: 3 escenarios de riesgo pais x 2 estrategias (A repagar caucion en Cocos / B T-bills afuera).
Modelo mensual nov-2026 .. oct-2029 (vencimiento AO29). Uso: python proyeccion_largo_plazo.py [--recovery 0.40] [--ret-otros 0.0] [--caucion-tasa 0.5] [--json]
Simplificaciones (ver docstring de cada bloque): bonos valuados con TIR = UST + spread; AO29 con flujos reales (bullet 6%);
los demas soberanos como bono sintetico calibrado a precio y duration de BondTerminal; cupones devengados mensualmente."""
import json, sys, math, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--recovery", type=float, default=0.40)       # valor de los bonos tras default/canje (fraccion del nominal); -1 = precio implicito en el riesgo pais del escenario
ap.add_argument("--ret-otros", type=float, default=0.0)       # retorno anual de activos no-AR (ETFs, IBKR, HSBC, notas)
ap.add_argument("--caucion-tasa", type=float, default=0.5)    # TNA % caucion USD
ap.add_argument("--tbill", type=float, default=4.1)           # TNA % T-bills
ap.add_argument("--election-m", type=int, default=12)         # mes 12 = oct-2027
ap.add_argument("--json", action="store_true")
args = ap.parse_args()

RP0 = 795.7
UST = lambda T: 4.6 if T <= 3.5 else 4.9
# bono: (valor_usd, precio, ytm%, moddur, gspread_pb)
BONOS = {"AO29": (560480, 81.95, 13.76, 2.54, 911), "AL35": (67503, 66.29, 12.74, 4.86, 797), "AE38": (66877, 68.86, 13.38, 3.93, 863),
         "AL41": (16636, 61.30, 12.78, 5.06, 794), "GD46": (4841, 59.89, 11.29, 5.54, 635), "GD29": (213, 54.85, 7.51, 1.33, 306)}
OTROS_COCOS = 797457 - 716549          # notas BBVA, FCI, cash (plano)
NO_COCOS = 1127671 - 797457            # Citi, IBKR, HSBC (crece a ret_otros)
CAUCION0 = 460035

def price(y, c, T):
    """Precio por 100 con cupon c%/anio continuo (devengo) y vencimiento T anios; T<=0 -> 100."""
    if T <= 0: return 100.0
    y /= 100; v = (1 + y / 2) ** (-2 * T)
    return c / 100 * (1 - v) / y * 100 + 100 * v

def mdur(y, c, T, h=0.01):
    """Duration modificada numerica (en anios)."""
    return -(price(y + h, c, T) - price(y - h, c, T)) / (2 * h) / price(y, c, T) * 100

def yield_implicito(P0, c, T):
    lo, hi = 0.5, 80.0
    for _ in range(80):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if price(mid, c, T) > P0 else (lo, mid)
    return (lo + hi) / 2

def calibrar(P0, y0, D0):
    """Encuentra (c, T) tal que price == P0 y mdur == D0 (bisección sobre T)."""
    best = None
    lo, hi = 0.3, 25.0
    def c_de(T):
        y = y0 / 100; v = (1 + y / 2) ** (-2 * T); A = (1 - v) / y
        return (P0 / 100 - v) / A * 100
    f = lambda T: mdur(y0, max(c_de(T), 0), T) - D0
    for _ in range(80):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if f(mid) < 0 else (lo, mid)
    T = (lo + hi) / 2
    return max(c_de(T), 0), T

POS = {}
for k, (val, P0, y0, D0, g) in BONOS.items():
    if k == "AO29":
        c, T0 = 6.0, 3.0
        g = (yield_implicito(P0, c, T0) - UST(T0)) * 100      # spread que reproduce el precio de mercado
    else: c, T0 = calibrar(P0, y0, D0)
    POS[k] = {"face": val / (P0 / 100), "c": c, "T0": T0, "g": g}

# ahorro mensual (fin de mes), m=1 es nov-2026
def ahorro(m):
    y, mo = divmod(10 + m, 12); yy = 2026 + y; mm = mo if mo else 12
    if mo == 0: yy -= 1
    f = {(2026, 11): 15000, (2026, 12): 15000, (2027, 1): 80000, (2027, 2): 20000, (2027, 3): 20000}
    if (yy, mm) in f: return f[(yy, mm)]
    if yy == 2027 and 4 <= mm <= 12: return 6000
    if yy == 2028 and mm == 1: return 100000
    if (yy == 2028 and mm >= 2) or (yy == 2029 and mm <= 10): return 3000
    return 0
def fecha(m):
    t = 10 + m; return f"{2026 + (t - 1) // 12}-{(t - 1) % 12 + 1:02d}"

ESCENARIOS = {"S1 Milei reelecto (RP 300)": 300, "S2 Centro con riesgo (RP 1000)": 1000, "S3 Default/canje (RP 2000)": 2000}
DEFAULT_M = 14   # dic-2027: se frenan cupones y el precio pasa a valor de recupero

def correr(rp, estrategia):
    caucion, tbills = CAUCION0, 0.0
    no_cocos = NO_COCOS; defaulted = False
    rows = []
    for m in range(0, 37):
        if m > 0: no_cocos *= (1 + args.ret_otros / 100) ** (1 / 12)
        post = m >= args.election_m
        scn_default = (rp >= 2000)
        defaulted = scn_default and m >= DEFAULT_M
        ar = 0.0; cupon = 0.0; venc = 0.0
        for k, p in POS.items():
            T = p["T0"] - m / 12
            if T <= 0 and not defaulted and m == 36 and k == "AO29": T = 0
            spread = p["g"] if not post else rp * p["g"] / RP0
            y = UST(max(T, 0.01)) + spread / 100
            px = price(y, p["c"], T) if T > 0 else 100.0
            if defaulted:
                if args.recovery < 0:      # modo mercado: congela el precio implicito en el riesgo pais del escenario (dic-27)
                    T14 = p["T0"] - DEFAULT_M / 12
                    px = price(UST(max(T14, 0.01)) + rp * p["g"] / RP0 / 100, p["c"], T14)
                else: px = args.recovery * 100
            val = p["face"] * px / 100
            if k == "AO29" and m == 36 and not defaulted: venc = val; val = 0.0
            ar += val
            if m > 0 and not defaulted and not (k == "AO29" and m == 36 and T <= 0): cupon += p["face"] * p["c"] / 100 / 12
        if m == 0: pass
        else:
            inflow = ahorro(m) + cupon - caucion * args.caucion_tasa / 100 / 12 + venc
            tbills *= (1 + args.tbill / 100 / 12)
            if estrategia == "A":
                rep = min(inflow, caucion); caucion -= rep; tbills += inflow - rep
            else:
                rep = min(venc, caucion) if venc else 0.0      # al vencer el AO29 expira el colateral: se cancela la caucion
                caucion -= rep; tbills += inflow - rep
        cocos_gross = ar + OTROS_COCOS
        gross = cocos_gross + no_cocos + tbills
        neto = gross - caucion; cn = cocos_gross - caucion
        rows.append({"m": m, "fecha": fecha(m) if m else "2026-10", "ar": round(ar), "caucion": round(caucion), "tbills": round(tbills),
                     "bruto": round(gross), "neto": round(neto), "lev_global": round(gross / neto, 2) if neto > 0 else None,
                     "cocos_neto": round(cn), "lev_cocos": round(cocos_gross / cn, 2) if cn > 0 else None,
                     "ar_pct_neto": round(100 * ar / neto, 1) if neto > 0 else None})
    return rows

if __name__ == "__main__":
    out = {"calibracion": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in POS.items()}, "resultados": {}}
    for nombre, rp in ESCENARIOS.items():
        for e in ("A", "B"):
            out["resultados"][f"{nombre} | {e}"] = correr(rp, e)
    if args.json: print(json.dumps(out, ensure_ascii=False))
    else:
        print("Calibracion bonos sinteticos:", {k: (round(v["c"], 2), round(v["T0"], 2)) for k, v in POS.items()})
        chk = [3, 5, 12, 14, 26, 36]
        for nombre, res in out["resultados"].items():
            print("\n" + nombre)
            for r in res:
                if r["m"] in [0] + chk:
                    print(" ", r["fecha"], {k: r[k] for k in ("ar", "caucion", "tbills", "neto", "lev_global", "lev_cocos", "ar_pct_neto")})
