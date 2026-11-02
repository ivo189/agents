#!/usr/bin/env python3
"""Arma la fila semanal para la planilla 'Evolucion Ratio apalancamiento' (Google Sheets).
Uso: python serie_apalancamiento.py --row N --fecha YYYY-MM-DD --bruto X --caucion X --cocos-bruto X --ar X --mep X --riesgo X --nota "..."
Imprime JSON {"range": "'Hoja 1'!A<N>", "formulas": [[...]]} para mcp__Google_Sheets__update_formulas.
N = primera fila vacía (última fila con fecha + 1; leer 'Hoja 1'!A:A con get_values). Columnas: A fecha, B bruto, C caución,
D =B-C, E =B/D, F Cocos bruto, G =F-C, H =F/G, I AR soberano, J =I/D, K MEP, L riesgo país, M nota."""
import argparse, json
p = argparse.ArgumentParser()
p.add_argument("--row", type=int, required=True); p.add_argument("--fecha", required=True)
for k in ("bruto", "caucion", "cocos-bruto", "ar", "mep", "riesgo"): p.add_argument("--" + k, type=float, required=True)
p.add_argument("--nota", default="")
a = p.parse_args(); r = a.row
if a.bruto <= a.caucion or a.cocos_bruto <= a.caucion:
    raise SystemExit("ERROR: neto <= 0; revisar bruto/caución/cocos-bruto antes de escribir")
row = [a.fecha, round(a.bruto), round(a.caucion), f"=B{r}-C{r}", f"=B{r}/D{r}", round(a.cocos_bruto), f"=F{r}-C{r}", f"=F{r}/G{r}",
       round(a.ar), f"=I{r}/D{r}", a.mep, a.riesgo, a.nota]
print(json.dumps({"range": f"'Hoja 1'!A{r}", "formulas": [row]}, ensure_ascii=False, indent=1))
