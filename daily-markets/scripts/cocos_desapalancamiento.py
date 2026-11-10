#!/usr/bin/env python3
"""Capítulo Cocos: plan de desapalancamiento de la cuenta (caución USD) con precios de mercado actuales.
Opciones por mes (nov-26 a dic-27) con el calendario de aportes de Ivo:
  A0  enviar USD y repagar caución directo (sin canje cable->MEP)
  A1  canjear cable->MEP (captura la brecha) y repagar caución
  B1  canjear y comprar AO27 (TIR MEP 4,1%) reinvirtiendo cupones
  B2  canjear y comprar ON corta (SUPUESTO: TIR 7%, duration 1,5; reemplazar por datos reales)
  M   50% repago (A1) + 50% AO27 (B1)
Uso: python cocos_desapalancamiento.py [--json] [--gap 5.0] [--on-tir 7.0] [--ao27-tir 4.09]"""
import json, argparse
ap = argparse.ArgumentParser()
ap.add_argument("--gap", type=float, default=5.5)        # % neto de captura al canjear cable->MEP: ~6% bruto (AL30C/AL30D) menos ~0,5 de spread; Cocos no cobra comisión por el canje (Ivo, 6-nov-26)
ap.add_argument("--ao27-tir", type=float, default=4.09)  # TIR MEP AO27 (BondTerminal 6-nov-26)
ap.add_argument("--on-tir", type=float, default=4.6)     # TIR MEP de ON Pampa corta (MGCN 4,57% / MGCT 4,61%), ver scripts/on_pampa.py
ap.add_argument("--caucion-tasa", type=float, default=1.5)   # 0,5 % de mercado + 1 pp de comisión de Cocos
ap.add_argument("--json", action="store_true")
a = ap.parse_args()

POS = {"AO29": (682075, 76.68, 2.47), "AL35": (99911, 62.31, 4.75), "AE38": (94310, 65.19, 3.78), "AL41": (26543, 58.21, 4.89), "GD46": (7760, 57.73, 5.36), "GD29": (385, 52.81, 1.27)}
AR0 = sum(n * p / 100 for n, p, d in POS.values()); DUR = sum(n * p / 100 * d for n, p, d in POS.values()) / AR0
NOTAS0, OTROS, CAUC0 = 70000, 9798, 460035
FACE_AO29 = 682075 / 0.7668 * 0.7668   # nominal 682.075
def aportes(m):  # m=1 nov-26
    if m in (1, 2): return 15000
    if m == 3: return 80000
    if m in (4, 5): return 20000
    if 6 <= m <= 14: return 6000
    return 0
def cupones(m):
    c = 682075 * 0.005                                   # AO29 mensual 0,5%
    c += 79 * (m <= 19) + 300 * (m <= 21) + (1500 if m >= 5 and (m - 5) % 3 == 0 else 0)   # notas
    if m % 6 == 3: c += 5000                             # resto de soberanos, ene/jul (aprox.)
    return c
LAB = lambda m: ["oct-26", "nov-26", "dic-26", "ene-27", "feb-27", "mar-27", "abr-27", "may-27", "jun-27", "jul-27", "ago-27", "sep-27", "oct-27", "nov-27", "dic-27"][m]
OPC = {"A0": ("Repagar directo (sin canje)", 0.0, 0.0), "A1": ("Canjear y repagar", a.gap, 0.0), "B1": ("Canjear y comprar AO27", a.gap, 1.0), "B2": ("Canjear y comprar ON Pampa corta (MGCN/MGCT)", a.gap, 1.0), "M": ("Mixta 50/50: repagar y AO27", a.gap, 0.5)}
YLD = {"B1": a.ao27_tir, "B2": a.on_tir, "M": a.ao27_tir}
DURB = {"B1": 0.92, "B2": 2.0, "M": 0.92}

def correr(op, shock_bp=0, shock_m=3, horizonte=14):
    nombre, g, share_buy = OPC[op]; y = YLD.get(op, 0)
    caucion, activo_b, rows = CAUC0, 0.0, []
    for m in range(0, horizonte + 1):
        ar = AR0 * (1 - DUR * shock_bp / 10000 * (m >= shock_m))
        if m > 0:
            activo_b *= 1 + y / 100 / 12
            flujo = aportes(m) * (1 + g / 100) + cupones(m) - caucion * a.caucion_tasa / 100 / 12
            comprar = flujo * share_buy; repagar = flujo - comprar
            rep = min(repagar, caucion); caucion -= rep; activo_b += comprar + (repagar - rep)
        ab = activo_b * (1 - DURB.get(op, 0) * shock_bp / 10000 * (m >= shock_m)) if op in DURB else activo_b
        gross = ar + NOTAS0 + OTROS + ab; net = gross - caucion
        rows.append({"m": m, "fecha": LAB(m), "bruto": round(gross), "caucion": round(caucion), "neto": round(net), "lev": round(gross / net, 2) if net > 0 else None, "activo_b": round(ab)})
    return rows

def meses_hasta(rows, L):
    for r in rows:
        if r["lev"] is not None and r["lev"] <= L: return r["fecha"]
    return "no llega"

# Cotizaciones IOL (último operado, 6-nov-2026): (precio D=MEP, precio C=cable, monto operado D, monto operado C en USD)
IOL = {"AL30": (51.51, 48.60, 7468105, 7629486), "GD30": (53.07, 50.00, 68937, 7843), "AL35": (63.70, 60.44, 393874, 54692), "GD35": (68.61, 65.15, 101390, 13865),
       "AO27": (102.15, 96.35, 218311, 66477), "AO29": (76.99, 72.90, 106156, 25226)}

def extras():
    import importlib.util as _u, os
    _sp = _u.spec_from_file_location("on_pampa", os.path.join(os.path.dirname(os.path.abspath(__file__)), "on_pampa.py")); _m = _u.module_from_spec(_sp); _sp.loader.exec_module(_m)
    T, g = 0.98, a.gap / 100
    brecha = {k: {"gap_pct": round(100 * (pd / pc - 1), 2), "monto_D": v[2], "monto_C": v[3]} for k, v in IOL.items() for pd, pc in [(v[0], v[1])]}
    comp = {"tbill_afuera": round(100 * 1.041 ** T, 1), "ao27_canje_queda_local": round(100 * (1 + g) * (1 + a.ao27_tir / 100) ** T, 1),
            "ao27_canje_repatria": round(100 * (1 + a.ao27_tir / 100) ** T, 1), "repagar_caucion_canje": round(100 * (1 + g) * (1 + a.caucion_tasa / 100 * T), 1)}
    def bp3(op, m, L=3.0):
        lo, hi = 0, 6000
        for _ in range(40):
            mid = (lo + hi) / 2; r = correr(op, mid, shock_m=m)[m]["lev"]
            (lo, hi) = (lo, mid) if (r is None or r >= L) else (mid, hi)
        return round((lo + hi) / 2)
    meses = [{"fecha": LAB(m), "A1": correr("A1")[m]["lev"], "A1_bp": bp3("A1", m), "B1": correr("B1")[m]["lev"], "B1_bp": bp3("B1", m)} for m in range(0, 4)]
    G = AR0 + NOTAS0 + OTROS; puente = []
    for X in (0, 40000, 60000, 87000, 128000):
        D = CAUC0 - X; puente.append({"X": X, "lev": round(G / (G - D), 2), "bp_3x": round((G - 1.5 * D) / (AR0 * DUR) * 10000)})
    _e = _u.spec_from_file_location("estr", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cocos_estrategia.py")); _em = _u.module_from_spec(_e); import sys as _sys; _old = _sys.argv; _sys.argv = ["x"]; _e.loader.exec_module(_em); _sys.argv = _old
    return {"estrategia": _em.run(), "on_pampa": _m.datos(), "brecha": brecha, "comparacion_100": comp, "meses_expuestos": meses, "puente": puente}

def main():
    G0 = AR0 + NOTAS0 + OTROS; N0 = G0 - CAUC0; L0 = G0 / N0
    req = []
    for L in (2.4, 2.2, 2.0, 1.8, 1.5):
        X = G0 / L - N0; Y = CAUC0 * L / (L - 1) - G0
        req.append({"L": L, "repagar_usd": round(max(X, 0)), "comprar_usd": round(max(Y, 0)), "desde_afuera_repagar": round(max(X, 0) / (1 + a.gap / 100)), "desde_afuera_comprar": round(max(Y, 0) / (1 + a.gap / 100))})
    base = {op: correr(op) for op in OPC}
    shocks = {bp: {op: correr(op, bp) for op in OPC} for bp in (150, 300, 600)}
    # colchon: caida del riesgo pais (pb) para llegar a 3x/4x hoy y en ene-27 por opcion
    def bp_para(L, op, m):
        lo, hi = 0, 4000
        for _ in range(40):
            mid = (lo + hi) / 2; r = correr(op, mid, shock_m=0)[m]["lev"]
            (lo, hi) = (lo, mid) if (r is None or r >= L) else (mid, hi)
        return round((lo + hi) / 2)
    colchon = {op: {"hoy_3x": bp_para(3.0, op, 0) if op == "A0" else None, "ene27_3x": bp_para(3.0, op, 3), "ene27_4x": bp_para(4.0, op, 3)} for op in OPC}
    out = {"estado_hoy": {"ar_usd": round(AR0), "duration_ar": round(DUR, 2), "notas": NOTAS0, "otros": OTROS, "bruto": round(G0), "caucion": CAUC0, "neto": round(N0), "apalancamiento": round(L0, 2)},
           "parametros": vars(a), "requerido": req, "opciones": {op: OPC[op][0] for op in OPC}, "caminos": base, "shocks": {str(k): v for k, v in shocks.items()}, "colchon_bp": colchon,
           "extras": extras(), "hitos": {op: {str(L): meses_hasta(base[op], L) for L in (2.4, 2.2, 2.0, 1.8, 1.5)} for op in OPC}}
    if a.json: print(json.dumps(out, ensure_ascii=False))
    else:
        print(json.dumps(out["estado_hoy"])); 
        for r in req: print(r)
        for op in OPC: print(op, OPC[op][0], [(r["fecha"], r["lev"]) for r in base[op] if r["m"] in (0, 3, 5, 8, 12, 14)], out["hitos"][op])
        print("colchon", colchon)
        for bp in (150, 300, 600): print("shock", bp, {op: shocks[bp][op][3]["lev"] for op in OPC})
if __name__ == "__main__": main()
