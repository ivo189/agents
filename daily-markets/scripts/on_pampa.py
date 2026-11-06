#!/usr/bin/env python3
"""TIR y duration de ONs de Pampa Energía (supuesto: bullet al vencimiento, cupón semestral, precios 'último operado' de IOL, liquidación hoy).
Salida JSON. Datos de cupón/vencimiento: captura de pantalla de Ivo (6-nov-2026). Precios: IOL (D = MEP, C = cable)."""
import json, datetime as dt
HOY = dt.date(2026, 11, 6)
# ticker base: (venc, cupon%, proximo cupon, ley, precio_D, precio_C, monto_D_usd, monto_C_usd)
ON = {"MGCQ": (dt.date(2028, 8, 6), 7.2, dt.date(2027, 2, 6), "ARG", 107.80, 102.00, 998, 10327),
      "MGCN": (dt.date(2028, 10, 4), 5.8, dt.date(2027, 4, 4), "ARG", 102.20, None, 548, None),
      "MGCT": (dt.date(2029, 4, 1), 5.5, dt.date(2027, 4, 1), "ARG", 102.00, 96.00, 10179, 960),
      "MGCU": (dt.date(2030, 8, 21), 5.5, dt.date(2027, 2, 21), "ARG", 99.50, None, 73661, None),
      "MGCM": (dt.date(2031, 9, 10), 8.0, dt.date(2027, 3, 10), "NY", 107.40, None, 32200, None),
      "MGCO": (dt.date(2034, 12, 16), 7.9, dt.date(2026, 12, 16), "NY", 105.95, None, 10595, None)}
def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12); return dt.date(d.year + y, m + 1, min(d.day, 28 if m == 1 else 30 if m + 1 in (4, 6, 9, 11) else 31))
def flujos(venc, cup, prox):
    fl = []; d = prox
    while d <= venc: fl.append((d, cup / 2 + (100 if d >= venc - dt.timedelta(days=3) else 0))); d = add_months(d, 6)
    return fl
def precio(y, fl):
    return sum(c / (1 + y / 2) ** (2 * (d - HOY).days / 365) for d, c in fl)
def ytm(dirty, fl):
    lo, hi = -0.5, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2; (lo, hi) = (mid, hi) if precio(mid, fl) > dirty else (lo, mid)
    return (lo + hi) / 2
def calc(t, px):
    venc, cup, prox, ley, *_ = ON[t]; fl = flujos(venc, cup, prox)
    ult = add_months(prox, -6); per = (prox - ult).days; dev = cup / 2 * (HOY - ult).days / per
    y = ytm(px + dev, fl); h = 1e-4
    dur = -(precio(y + h, fl) - precio(y - h, fl)) / (2 * h) / precio(y, fl) / (1 + 0) * 1 / 1
    anios = (venc - HOY).days / 365
    return {"ytm_pct": round(100 * y, 2), "mod_dur": round(dur, 2), "anios": round(anios, 2), "devengado": round(dev, 2), "cy_pct": round(100 * cup / px, 2)}
def datos():
    out = {}
    for t, (venc, cup, prox, ley, pD, pC, mD, mC) in ON.items():
        r = {"vencimiento": str(venc), "cupon_pct": cup, "ley": ley, "precio_D": pD, "precio_C": pC, "monto_operado_D_usd": mD, "monto_operado_C_usd": mC, "mep": calc(t, pD)}
        if pC: r["cable"] = calc(t, pC); r["brecha_pct"] = round(100 * (pD / pC - 1), 2)
        else: r["cable_est"] = calc(t, round(pD / 1.0575, 2))
        out[t] = r
    return out

if __name__ == "__main__":
    print(json.dumps(datos(), ensure_ascii=False, indent=1))
