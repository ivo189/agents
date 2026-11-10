#!/usr/bin/env python3
"""Proyección de la cuenta de Cocos sola (nov-2026 a oct-2029, vence el AO29): 3 escenarios x 3 previas x 4 alternativas.
Punto de partida: posiciones del estado de Cocos (31/10) a precios de BondTerminal del 6/11/2026 (MEP), caución USD 460.035.
Alternativas (Ivo, 10-nov-2026):
  N  'Nada'            : sin capital nuevo. Los flujos de la cuenta (cupones, amortizaciones, vencimientos de notas) repagan caución.
  R  'Repagar caución' : capital nuevo (nov 15k, dic 15k, ene 70k, feb 15k, mar 15k = 130k) se canjea cable->MEP y repaga caución.
  F  'Fondo USD'       : el capital nuevo va al fondo conservador USD de Cocos (~4,5 % anual); los flujos de la cuenta repagan caución.
  A  'AO29 si RP>700'  : el capital nuevo compra AO29 a precio de mercado si el riesgo país está por arriba de 700 pb;
                         por debajo de 700 no compra y lo deja en el fondo USD. Los cupones del AO29 nuevo también repagan caución.
En todas: todo flujo que entra (cupones, vencimientos) repaga caución; una vez cerrada, el excedente va al fondo USD.
Regla de venta escalonada de largos (AL35/AE38/AL41/GD46/GD29): RP <= 600 vende 25 %, <= 500 llega a 50 %, <= 400 a 100 %;
lo producido repaga caución (desactivar con --sin-regla).
Escenarios desde la elección (oct-2027): S1 Milei reelecto -> RP 200; S2 Oposición con shock -> 1.600 pb por 6 meses y baja lineal
a 900 en oct-2029; S3 Reestructuración (canje) -> RP 2.000, default dic-2027 (sin cupones), canje jun-2028 de todos los soberanos
a un bono nuevo (quita 25 % del nominal, cupón 5 % semestral, vence jul-2035); RP baja lineal de 2.000 (jun-28) a 1.200 (oct-29).
Desde la elección, el soberano se valúa como (1 - quita) x precio del bono nuevo a TIR UST + RP (--quita, --cupon-nuevo, --s3-end).
Previas (nov-26 a sep-27, comunes a los 3 escenarios), desde 938 pb: '800' baja a 800 en mar-27; '1000' sube a 1.000 en sep-27;
'1200' sube a 1.200 en sep-27.
Uso: proyeccion_cocos.py [--previa 800|1000|1200] [--recovery -1|0.40] [--s1 200] [--gap 5.5] [--fondo 4.5] [--umbral-ao29 700] [--json]"""
import json, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--previa", default="1000", choices=["800", "1000", "1200"])
ap.add_argument("--recovery", type=float, default=-1, help="(obsoleto) S3 ahora se modela como canje")
ap.add_argument("--quita", type=float, default=25, help="S3: quita de nominal en el canje (%%)")
ap.add_argument("--cupon-nuevo", type=float, default=5.0, help="S3: cupón anual del bono nuevo (semestral)")
ap.add_argument("--s3-end", type=float, default=1200, help="S3: riesgo país en oct-2029 (baja lineal desde el canje)")
ap.add_argument("--s1", type=float, default=200)
ap.add_argument("--s2-peak", type=float, default=1600); ap.add_argument("--s2-hold", type=int, default=6); ap.add_argument("--s2-end", type=float, default=900)
ap.add_argument("--gap", type=float, default=5.6, help="captura neta del canje cable->MEP (%%)")
ap.add_argument("--fondo", type=float, default=4.5, help="rendimiento anual del fondo conservador USD de Cocos (%%)")
ap.add_argument("--caucion-tasa", type=float, default=0.5)
ap.add_argument("--umbral-ao29", type=float, default=700)
ap.add_argument("--sin-regla", action="store_true")
ap.add_argument("--json", action="store_true")
args, _ = ap.parse_known_args()

RP0 = 937.9                     # BondTerminal 6/11/2026 17:00
UST = lambda T: 4.6 if T <= 3.5 else 4.9
# nominal (VN), precio MEP, TIR, duration modificada (BondTerminal 6/11/2026)
BONOS = {"AO29": (682075, 76.82, 16.40, 2.47), "AL35": (99911, 61.79, 14.22, 4.73), "AE38": (94310, 64.51, 15.10, 3.75),
         "AL41": (26543, 58.14, 13.87, 4.88), "GD46": (7760, 58.10, 11.87, 5.38), "GD29": (385, 53.76, 9.21, 1.28)}
LARGOS = ("AL35", "AE38", "AL41", "GD46", "GD29")
CAUCION0, OTROS = 460035, 9798
NOTAS = [("MSFT/ORCL", 10000, lambda m: 79 if 1 <= m <= 19 else 0, 19),
         ("MELI/NU", 30000, lambda m: 300 if 1 <= m <= 21 else 0, 21),
         ("BBD/MELI/NU", 30000, lambda m: 1500 if 5 <= m <= 26 and (m - 5) % 3 == 0 else 0, 26)]
APORTES = {1: 15000, 2: 15000, 3: 70000, 4: 15000, 5: 15000}
ELEC, DEFAULT_M, CANJE_M, N = 12, 14, 20, 36       # elección oct-27, default dic-27, canje jun-28, fin oct-29
VTO_NUEVO = 2035.5                                  # bono nuevo del canje: vence jul-2035, cupón semestral desde el canje
PREVIAS = {"800": [(0, RP0), (5, 800), (11, 800)], "1000": [(0, RP0), (11, 1000)], "1200": [(0, RP0), (11, 1200)]}
ESTRATEGIAS = {"N": "Nada", "R": "Repagar caución", "F": "Fondo USD", "A": "AO29 si RP>700", "M": "Mitad fondo, mitad AO29", "P": "Fondo y repago antes de la elección"}

def price(y, c, T):
    if T <= 0: return 100.0
    y /= 100; v = (1 + y / 2) ** (-2 * T)
    return c / 100 * (1 - v) / y * 100 + 100 * v
def mdur(y, c, T, h=0.01): return -(price(y + h, c, T) - price(y - h, c, T)) / (2 * h) / price(y, c, T) * 100
def ytm_impl(P0, c, T):
    lo, hi = 0.5, 80.0
    for _ in range(80):
        mid = (lo + hi) / 2; (lo, hi) = (mid, hi) if price(mid, c, T) > P0 else (lo, mid)
    return (lo + hi) / 2
def calibrar(P0, y0, D0):
    def c_de(T):
        y = y0 / 100; v = (1 + y / 2) ** (-2 * T); return (P0 / 100 - v) / ((1 - v) / y) * 100
    lo, hi = 0.3, 25.0
    for _ in range(80):
        mid = (lo + hi) / 2; (lo, hi) = (mid, hi) if mdur(y0, max(c_de(mid), 0), mid) - D0 < 0 else (lo, mid)
    T = (lo + hi) / 2; return max(c_de(T), 0), T
POS = {}
for k, (vn, P0, y0, D0) in BONOS.items():
    if k == "AO29": c, T0 = 6.0, 3.0 - 1 / 12                     # bullet oct-29, cupón 6 % pagadero 0,5 % mensual
    else: c, T0 = calibrar(P0, y0, D0)                            # bullet sintético calibrado a precio y duration
    POS[k] = {"vn": vn, "c": c, "T0": T0, "g": (ytm_impl(P0, c, T0) - UST(T0)) * 100}

def interp(pts, m):
    if m <= pts[0][0]: return pts[0][1]
    for (m0, r0), (m1, r1) in zip(pts, pts[1:]):
        if m <= m1: return r1 if m1 == m0 else r0 + (r1 - r0) * (m - m0) / (m1 - m0)
    return pts[-1][1]
def escenarios():
    return {"S1": {"nombre": f"Milei reelecto (RP {int(args.s1)})", "post": [(ELEC, args.s1)], "default": False},
            "S2": {"nombre": f"Oposición con shock (RP {int(args.s2_peak)})", "post": [(ELEC, args.s2_peak), (ELEC + args.s2_hold, args.s2_peak), (N, args.s2_end)], "default": False},
            "S3": {"nombre": "Reestructuración (canje)", "post": [(ELEC, 2000), (CANJE_M, 2000), (N, args.s3_end)], "default": True}}
def rp_t(m, scn): return interp(PREVIAS[args.previa], m) if m < ELEC else interp(scn["post"], m)

def anios(m): return 2026 + (9 + m) / 12 + 1 / 12            # fin del mes m (m=0: oct-26)
def px_nuevo(m, scn):
    T = VTO_NUEVO - anios(m); return price(UST(T) + rp_t(m, scn) / 100, args.cupon_nuevo, T)
def px(k, m, scn):
    p = POS[k]; T = p["T0"] - m / 12
    if scn["default"] and m >= ELEC:                  # desde la elección el mercado precia el canje: (1 - quita) x bono nuevo
        return (1 - args.quita / 100) * px_nuevo(m, scn)
    return price(UST(max(T, 0.01)) + rp_t(m, scn) * p["g"] / RP0 / 100, p["c"], T) if T > 0 else 100.0

def fecha(m):
    t = 10 + m; return f"{2026 + (t - 1) // 12}-{(t - 1) % 12 + 1:02d}"

def correr(scn, est):
    vn = {k: p["vn"] for k, p in POS.items()}
    caucion, fondo = float(CAUCION0), float(OTROS)
    vendido = 0.0; acum = {"aportes": 0.0, "cupones": 0.0, "venc_notas": 0.0, "venta_largos": 0.0, "interes_caucion": 0.0, "compra_ao29": 0.0, "venc_ao29": 0.0, "rend_fondo": 0.0}
    rows = []
    for m in range(N + 1):
        rp = rp_t(m, scn); dflt = scn["default"] and m >= DEFAULT_M
        flujo = 0.0
        if m > 0:
            r = fondo * ((1 + args.fondo / 100) ** (1 / 12) - 1); fondo += r; acum["rend_fondo"] += r
            i = caucion * args.caucion_tasa / 100 / 12; acum["interes_caucion"] += i; flujo -= i
            if not dflt:
                c = vn["AO29"] * 0.005 + sum(vn[k] * POS[k]["c"] / 100 / 2 for k in LARGOS if m % 6 == 3)
                flujo += c; acum["cupones"] += c
            elif m > CANJE_M and (m - CANJE_M) % 6 == 0:
                c = sum(vn.values()) * (1 - args.quita / 100) * args.cupon_nuevo / 100 / 2
                flujo += c; acum["cupones"] += c
            for _, monto, cf, vm in NOTAS:
                flujo += cf(m); acum["cupones"] += cf(m)
                if m == vm: flujo += monto; acum["venc_notas"] += monto
            if m == N and not dflt:
                v = vn["AO29"]; flujo += v; acum["venc_ao29"] += v; vn["AO29"] = 0.0
            # regla de venta escalonada de largos
            if not args.sin_regla and not dflt:
                obj = 1.0 if rp <= 400 else 0.5 if rp <= 500 else 0.25 if rp <= 600 else 0.0
                if obj > vendido:
                    frac = (obj - vendido) / (1 - vendido)
                    v = sum(vn[k] * frac * px(k, m, scn) / 100 for k in LARGOS)
                    for k in LARGOS: vn[k] *= 1 - frac
                    vendido = obj; flujo += v; acum["venta_largos"] += v
            # capital nuevo
            ap_ = APORTES.get(m, 0) if est != "N" else 0
            if ap_:
                acum["aportes"] += ap_; x = ap_ * (1 + args.gap / 100)
                if est == "R": flujo += x
                elif est in ("F", "P"): fondo += x
                elif est in ("A", "M"):
                    y = x if est == "A" else x / 2
                    if rp > args.umbral_ao29: vn["AO29"] += y / (px("AO29", m, scn) / 100); acum["compra_ao29"] += y
                    else: fondo += y
                    fondo += x - y
            if est == "P" and m == ELEC - 1:             # sep-27: el fondo repaga caución antes de la elección
                u = min(fondo, caucion); fondo -= u; caucion -= u
            # todo flujo repaga caución; el excedente va al fondo (si el flujo es negativo, sale del fondo o suma caución)
            if flujo >= 0:
                rep = min(flujo, caucion); caucion -= rep; fondo += flujo - rep
            else:
                d = -flujo; u = min(d, fondo); fondo -= u; caucion += d - u
        ar = sum(vn[k] * px(k, m, scn) / 100 for k in POS)
        notas = sum(monto for _, monto, _, vm in NOTAS if m < vm)
        bruto = ar + notas + fondo; neto = bruto - caucion
        rows.append({"m": m, "fecha": fecha(m) if m else "2026-10", "rp": round(rp, 1), "ar": round(ar), "ao29": round(vn["AO29"] * px("AO29", m, scn) / 100),
                     "largos": round(sum(vn[k] * px(k, m, scn) / 100 for k in LARGOS)), "notas": notas, "fondo": round(fondo), "caucion": round(caucion),
                     "bruto": round(bruto), "neto": round(neto), "lev": round(bruto / neto, 2) if neto > 0 else None,
                     "neto_menos_aportes": round(neto - acum["aportes"]), "capacidad_2x": round(max(2 * neto - bruto, 0)),
                     **{k: round(v) for k, v in acum.items()}})
    return rows

def todo():
    out = {"parametros": {k: v for k, v in vars(args).items() if k != "json"}, "rp0": RP0, "aportes": APORTES, "estrategias": ESTRATEGIAS,
           "calibracion": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in POS.items()}, "resultados": {}}
    for s, scn in escenarios().items():
        out["resultados"][s] = {"nombre": scn["nombre"], "rp_path": [round(rp_t(m, scn), 1) for m in range(N + 1)],
                                "estrategias": {e: correr(scn, e) for e in ESTRATEGIAS}}
    return out

if __name__ == "__main__":
    o = todo()
    if args.json: print(json.dumps(o, ensure_ascii=False))
    else:
        r0 = o["resultados"]["S1"]["estrategias"]["N"][0]
        print("hoy", {k: r0[k] for k in ("ar", "ao29", "largos", "notas", "fondo", "caucion", "bruto", "neto", "lev")})
        for s, v in o["resultados"].items():
            for e, rows in v["estrategias"].items():
                print(s, v["nombre"], e, ESTRATEGIAS[e])
                for r in rows:
                    if r["m"] in (3, 5, 11, 12, 14, 24, 36):
                        print("  ", r["fecha"], {k: r[k] for k in ("rp", "ar", "fondo", "caucion", "neto", "lev", "neto_menos_aportes", "capacidad_2x")})
