#!/usr/bin/env python3
"""Convierte la salida de proyeccion_largo_plazo.py --json en la tabla 2D para la pestaña 'Proyección LP' del Google Sheet.
Uso: python proyeccion_a_sheet.py base.json > tabla.json   (imprime {"range": "...", "formulas": [[...]]} para update_formulas)
Layout: fila 1 titulo, fila 2 nota, fila 4 bloques, fila 5 encabezados, filas 6..42 = meses 0..36.
Bloques de 10 columnas: A..J apalancamiento global, L..U apalancamiento Cocos, W..AF patrimonio neto (USD), AH..AK posicion AR valuada.
Cada bloque: Fecha | S1-A | S1-A2 | S1-B | S2-A | S2-A2 | S2-B | S3-A | S3-A2 | S3-B (AR: Fecha | S1 | S2 | S3)."""
import json, sys, datetime
d = json.load(open(sys.argv[1])); R = d["resultados"]; E = ("A", "A2", "B")
MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
def lab(m):
    t = 10 + m - 1; return f"'{MES[t % 12]}-{str(2026 + t // 12)[2:]}" if m else "'oct-26"
def blk(key, nd):
    head = ["Fecha"] + [f"{s}·{e}" for s in R for e in E]
    rows = [[lab(m)] + [(None if R[s]["estrategias"][e][m][key] is None else (round(R[s]["estrategias"][e][m][key], nd) if nd else round(R[s]["estrategias"][e][m][key]))) for s in R for e in E] for m in range(37)]
    return head, rows
bl = [blk("lev_global", 2), blk("lev_cocos", 2), blk("neto", 0)]
arh = ["Fecha"] + [f"{s}" for s in R]; arr = [[lab(m)] + [round(R[s]["estrategias"]["A2"][m]["ar"]) for s in R] for m in range(37)]
titles = ["Apalancamiento global (bruto / neto)", "Apalancamiento de Cocos", "Patrimonio neto global (USD)", "Posición AR valuada (USD)"]
width = 40
grid = [[""] * width for _ in range(42)]
grid[0][0] = "Proyección de largo plazo · A: repagar todo · A2: 50% repago + 50% USA 60/40 · B: T-bills afuera"
grid[1][0] = f"Generado el {datetime.date.today().isoformat()} por el agente semanal. Escenarios: S1 riesgo país 300 · S2 1000 · S3 2000 (default). Supuestos en el repo (plan_largo_plazo.json)."
starts = [0, 11, 22, 33]
for i, (h, rows) in enumerate(bl + [(arh, arr)]):
    c0 = starts[i]; grid[3][c0] = titles[i]
    for j, v in enumerate(h): grid[4][c0 + j] = v
    for r, row in enumerate(rows):
        for j, v in enumerate(row): grid[5 + r][c0 + j] = "" if v is None else v
print(json.dumps({"range": "'Proyección LP'!A1", "formulas": grid}, ensure_ascii=False, separators=(",", ":")))
