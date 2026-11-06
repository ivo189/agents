#!/usr/bin/env python3
"""Bloque fijo del email semanal: 'Estrategia Cocos esta semana' (5 líneas).
Uso: estrategia_semanal.py --rp 934 --lev 2.6 --caucion 460035 [--mes 2026-11] [--html]
Compara apalancamiento real vs plan E1 (repagar todo), riesgo país vs escalones de venta (600/500/400 -> 25/50/100 % de largos, acumulado) y próximos aportes/cupones."""
import sys, json, argparse, importlib.util, os
ap = argparse.ArgumentParser()
ap.add_argument("--rp", type=float, required=True); ap.add_argument("--lev", type=float, required=True); ap.add_argument("--caucion", type=float, required=True)
ap.add_argument("--mes", default=None, help="AAAA-MM; por defecto el mes actual"); ap.add_argument("--vendido", type=float, default=0.0, help="fracción de largos ya vendida (0-1)")
ap.add_argument("--html", action="store_true"); a = ap.parse_args()
argv, sys.argv = sys.argv, [sys.argv[0]]
sp = importlib.util.spec_from_file_location("ce", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cocos_estrategia.py")); ce = importlib.util.module_from_spec(sp); sp.loader.exec_module(ce); sys.argv = argv
import datetime
hoy = datetime.date.today(); y, mth = (map(int, a.mes.split("-")) if a.mes else (hoy.year, hoy.month))
m = (y - 2026) * 12 + mth - 10                       # m=0 es oct-26
m = max(0, min(m, 14)); E1 = ce.run()["estrategias"]["E1"]["filas"]
plan = E1[m]; sig = E1[min(m + 1, 14)]
ESC = ((600, 25), (500, 50), (400, 100)); vend_pct = a.vendido * 100
proximo = next(((rp, p) for rp, p in ESC if p > vend_pct), None)
disp = [(rp, p) for rp, p in ESC if a.rp <= rp and p > vend_pct]
f = lambda v: f"{v:,.0f}".replace(",", ".")
desvio = a.lev - plan["lev_cocos"]
est = "adelantado" if desvio < -0.05 else "atrasado" if desvio > 0.05 else "en línea"
l = []
l.append(f"Apalancamiento de Cocos: {a.lev:.2f}x contra {plan['lev_cocos']:.2f}x del plan para {plan['fecha']} ({est}); caución USD {f(a.caucion)}.")
if disp:
    rp, p = disp[-1]; r = ce.regla_venta(rp, p / 100, a.rp)
    l.append(f"DISPARADOR ACTIVO: riesgo país {a.rp:.0f} pb <= {rp}: corresponde vender hasta {p} % de los largos (acumulado), producido estimado USD {f(r['producido'])}, apalancamiento resultante {r['lev_despues']:.2f}x (estimado con las posiciones del modelo; recalcular con el estado de Cocos vigente).")
elif proximo:
    l.append(f"Riesgo país {a.rp:.0f} pb: faltan {a.rp - proximo[0]:.0f} pb para el próximo escalón ({proximo[0]} pb: vender hasta {proximo[1]} % de los largos). No se vende hoy.")
else: l.append(f"Riesgo país {a.rp:.0f} pb: todos los escalones de venta ya ejecutados.")
l.append(f"Próximo mes ({sig['fecha']}): aporte previsto USD {f(ce.aporte(min(m + 1, 14)))} (se canjea cable a MEP y repaga caución) y cupones estimados USD {f(ce.cupones(min(m + 1, 14), True))}.")
l.append(f"Plan a {sig['fecha']}: caución USD {f(sig['caucion'])}, capacidad de compra a 2,0x USD {f(sig['firepower_2x'])}; a dic-27: {E1[14]['lev_cocos']:.2f}x y USD {f(E1[14]['firepower_2x'])}.")
l.append("Regla vigente: no se vende por encima de 600 pb de riesgo país; mientras tanto la caución se reduce solo con capital nuevo y cupones.")
if a.html:
    print("<h4>Estrategia Cocos esta semana</h4><ul>" + "".join(f"<li>{('<b>'+x+'</b>') if x.startswith('DISPARADOR') else x}</li>" for x in l) + "</ul>")
else: print("\n".join(l))
