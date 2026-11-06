#!/usr/bin/env python3
"""Bloques de valuación por camino previo de riesgo país (800/1000/1200) para la pestaña 'Proyección LP' (columnas AO en adelante).
Uso: python previas_a_sheet.py h_800.json h_1000.json h_1200.json [--graficos]   -> imprime {"range","formulas"} o los requests de gráficos.
Bloques (m=0..18): Cartera de Cocos (bonos AR + notas + efectivo), Cartera total (activos brutos, estrategia Mixta) y Patrimonio neto total (Mixta).
Por bloque: Fecha | para cada escenario: previa 800 | previa 1000 | previa 1200."""
import json, sys
files = [a for a in sys.argv[1:] if not a.startswith("--")]
V = [json.load(open(f))["resultados"] for f in files]
NM = 18; C0 = 40; STARTS = [C0, C0 + 11, C0 + 22]
MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
def lab(m):
    t = 10 + m - 1; return f"'{MES[t % 12]}-{str(2026 + t // 12)[2:]}" if m else "'oct-26"
PRE = ["previa 800 pb", "previa 1.000 pb", "previa 1.200 pb"]
fn = [("Cartera de Cocos (USD)", lambda r: r["cocos_neto"] + r["caucion"]), ("Cartera total: activos brutos (USD, estrategia Mixta)", lambda r: r["bruto"]), ("Patrimonio neto total (USD, estrategia Mixta)", lambda r: r["neto"])]
SC = list(V[0])
if "--graficos" not in sys.argv:
    W = STARTS[-1] + 10 - C0
    grid = [[""] * W for _ in range(24)]
    for b, (title, f) in enumerate(fn):
        c = STARTS[b] - C0; grid[3][c] = title
        for i, s in enumerate(SC):
            grid[2][c + 1 + 3 * i] = V[0][s]["nombre"]
            for j in range(3): grid[4][c + 1 + 3 * i + j] = PRE[j]
        grid[4][c] = "Fecha"
        for m in range(NM + 1):
            grid[5 + m][c] = lab(m)
            for i, s in enumerate(SC):
                for j in range(3): grid[5 + m][c + 1 + 3 * i + j] = f(V[j][s]["estrategias"]["A2"][m])
    print(json.dumps({"range": "'Proyección LP'!AO1", "formulas": grid}, ensure_ascii=False, separators=(",", ":")))
else:
    SID = 777
    def rgb(h): return {"rgbColor": {"red": round(int(h[1:3], 16) / 255, 4), "green": round(int(h[3:5], 16) / 255, 4), "blue": round(int(h[5:7], 16) / 255, 4)}}
    def rng(c): return {"sourceRange": {"sources": [{"sheetId": SID, "startRowIndex": 4, "endRowIndex": 5 + NM + 1, "startColumnIndex": c, "endColumnIndex": c + 1}]}}
    reqs = [{"updateSheetProperties": {"properties": {"sheetId": SID, "gridProperties": {"rowCount": 200, "columnCount": 80}}, "fields": "gridProperties.rowCount,gridProperties.columnCount"}}]
    for b, (title, f) in enumerate(fn):
        for i, s in enumerate(SC):
            series = [{"series": rng(STARTS[b] + 1 + 3 * i + j), "targetAxis": "LEFT_AXIS", "colorStyle": rgb("#444444"), "lineStyle": {"type": ["SOLID", "MEDIUM_DASHED", "DOTTED"][j], "width": 2}} for j in range(3)]
            reqs.append({"addChart": {"chart": {"spec": {"title": f"{V[0][s]['nombre']} · {title.split(' (')[0]} según la previa", "basicChart": {"chartType": "LINE", "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
                "axis": [{"position": "BOTTOM_AXIS", "title": "Mes"}, {"position": "LEFT_AXIS", "title": "USD"}], "domains": [{"domain": rng(STARTS[b])}], "series": series}},
                "position": {"overlayPosition": {"anchorCell": {"sheetId": SID, "rowIndex": 122 + 19 * b, "columnIndex": 5 * i}, "widthPixels": 470, "heightPixels": 330}}}}})
    print(json.dumps(reqs, ensure_ascii=False, separators=(",", ":")))
