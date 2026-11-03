#!/usr/bin/env python3
"""Genera los requests (batchUpdate) para recrear los 10 gráficos de la pestaña 'Proyección LP'.
Uso: python graficos_sheet.py [--borrar id1,id2,...] > requests.json   (sheetId de la pestaña = 777)
Series: Reducir caución (sólido, azul), Mixta (raya, naranja), T-bills (punteado, verde); encabezados en la fila 5."""
import json, sys
SID = 777
def rgb(h): return {"rgbColor": {"red": round(int(h[1:3], 16) / 255, 4), "green": round(int(h[3:5], 16) / 255, 4), "blue": round(int(h[5:7], 16) / 255, 4)}}
COL = ["#2a78d6", "#eb6834", "#1baf7a"]; DASH = ["SOLID", "MEDIUM_DASHED", "DOTTED"]
def rng(c): return {"sourceRange": {"sources": [{"sheetId": SID, "startRowIndex": 4, "endRowIndex": 42, "startColumnIndex": c, "endColumnIndex": c + 1}]}}
def chart(title, dom, cols, row, col, w=470, ytitle="", solid=False):
    series = [{"series": rng(c), "targetAxis": "LEFT_AXIS", "colorStyle": rgb(COL[i]), "lineStyle": {"type": "SOLID" if solid else DASH[i], "width": 2}} for i, c in enumerate(cols)]
    return {"addChart": {"chart": {"spec": {"title": title, "basicChart": {"chartType": "LINE", "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
            "axis": [{"position": "BOTTOM_AXIS", "title": "Mes"}, {"position": "LEFT_AXIS", "title": ytitle}], "domains": [{"domain": rng(dom)}], "series": series}},
            "position": {"overlayPosition": {"anchorCell": {"sheetId": SID, "rowIndex": row, "columnIndex": col}, "widthPixels": w, "heightPixels": 330}}}}}
reqs = []
if "--borrar" in sys.argv:
    for i in sys.argv[sys.argv.index("--borrar") + 1].split(","): reqs.append({"deleteEmbeddedObject": {"objectId": int(i)}})
esc = ["Milei reelecto (RP 300)", "Oposición con shock (RP 1600)", "Reestructuración (RP 2000)"]
for nm, c0, row, yt in (("Apalancamiento global", 0, 44, "Veces (x)"), ("Apalancamiento de Cocos", 11, 63, "Veces (x)"), ("Patrimonio neto global (USD)", 22, 82, "USD")):
    for i, s in enumerate(esc): reqs.append(chart(f"{s} · {nm}", c0, [c0 + 1 + 3 * i, c0 + 2 + 3 * i, c0 + 3 + 3 * i], row, i * 5, 470, yt))
reqs.append(chart("Posición en bonos AR valuada (USD) por escenario", 33, [34, 35, 36], 101, 0, 720, "USD", solid=True))
print(json.dumps(reqs, ensure_ascii=False, separators=(",", ":")))
