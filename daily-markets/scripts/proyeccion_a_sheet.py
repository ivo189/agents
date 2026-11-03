#!/usr/bin/env python3
"""Convierte la salida de proyeccion_largo_plazo.py --json en la tabla 2D para la pestaña 'Proyección LP' del Google Sheet.
Uso: python proyeccion_a_sheet.py base.json > tabla.json   (imprime {"range": "...", "formulas": [[...]]} para update_formulas)
Layout: fila 1 titulo, fila 2 nota, fila 3 escenarios, fila 4 bloques, fila 5 encabezados (nombres de estrategia), filas 6..42 = meses 0..36.
Bloques de 10 columnas: A..J apalancamiento global, L..U apalancamiento Cocos, W..AF patrimonio neto (USD), AH..AK posicion AR valuada.
Cada bloque: Fecha | (por escenario) Reducir caución | Mixta | T-bills (AR: Fecha | un escenario por columna). Previa de riesgo país = la del JSON de entrada."""
import json, sys, datetime
d = json.load(open(sys.argv[1])); R = d["resultados"]; E = ("A", "A2", "B"); NOM = {"A": "Reducir caución", "A2": "Mixta", "B": "T-bills"}
MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
def lab(m):
    t = 10 + m - 1; return f"'{MES[t % 12]}-{str(2026 + t // 12)[2:]}" if m else "'oct-26"
def blk(key, nd):
    head = ["Fecha"] + [NOM[e] for s in R for e in E]
    rows = [[lab(m)] + [(None if R[s]["estrategias"][e][m][key] is None else (round(R[s]["estrategias"][e][m][key], nd) if nd else round(R[s]["estrategias"][e][m][key]))) for s in R for e in E] for m in range(37)]
    return head, rows
bl = [blk("lev_global", 2), blk("lev_cocos", 2), blk("neto", 0)]
arh = ["Fecha"] + [R[s]["nombre"] for s in R]; arr = [[lab(m)] + [round(R[s]["estrategias"]["A2"][m]["ar"]) for s in R] for m in range(37)]
titles = ["Apalancamiento global (bruto / neto)", "Apalancamiento de Cocos", "Patrimonio neto global (USD)", "Posición AR valuada (USD)"]
width = 40
grid = [[""] * width for _ in range(42)]
grid[0][0] = "Proyección de largo plazo · Reducir caución: todo repaga caución · Mixta: 50% caución + 50% USA 60/40 · T-bills: todo a T-bills afuera"
grid[1][0] = f"Generado el {datetime.date.today().isoformat()} por el agente semanal. Previa de riesgo país 800 pb (actual); aportes USD 367 mil; 6% anual para lo que no es Cocos. Supuestos en el repo (plan_largo_plazo.json)."
starts = [0, 11, 22, 33]
for c0 in starts[:3]:
    for i, sc in enumerate(R): grid[2][c0 + 1 + 3 * i] = R[sc]["nombre"]
for i, (h, rows) in enumerate(bl + [(arh, arr)]):
    c0 = starts[i]; grid[3][c0] = titles[i]
    for j, v in enumerate(h): grid[4][c0 + j] = v
    for r, row in enumerate(rows):
        for j, v in enumerate(row): grid[5 + r][c0 + j] = "" if v is None else v
print(json.dumps({"range": "'Proyección LP'!A1", "formulas": grid}, ensure_ascii=False, separators=(",", ":")))
