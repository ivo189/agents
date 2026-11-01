#!/usr/bin/env python3
"""Tasa de caución en dólares (1D) desde IOL. Uso: python caucion_usd.py [--html archivo]
Parsea https://iol.invertironline.com/mercado/cotizaciones/argentina/cauciones/todas .
Regla: filas DOLARES con tasa > 0, plazo más corto con monto relevante (plazo 1 de lunes a jueves;
los viernes/antes de feriado el '1 día' liquida a 3 días). Devuelve tasa (TNA %), plazo, monto, fecha/hora.
Si la rueda no operó, devuelve la última disponible y lo marca."""
import re, sys, json, urllib.request

URL = "https://iol.invertironline.com/mercado/cotizaciones/argentina/cauciones/todas"

def n(s): return float(s.replace(".", "").replace(",", ".").replace("%", "").strip())

def main():
    if "--html" in sys.argv: h = open(sys.argv[sys.argv.index("--html") + 1], encoding="utf-8", errors="ignore").read()
    else: h = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8", "ignore")
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S | re.I)
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, flags=re.S | re.I):
        c = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
        if len(c) >= 7 and c[1] == "DOLARES":
            rows.append({"plazo": int(c[0]), "monto": n(c[2]), "tasa": n(c[5]), "fecha_hora": c[6]})
    ok = [r for r in rows if r["tasa"] > 0 and r["monto"] >= 100_000]
    if not ok:
        print(json.dumps({"error": "sin cauciones USD con tasa>0", "filas": rows}, ensure_ascii=False)); sys.exit(1)
    corto = min(r["plazo"] for r in ok)
    pick = max((r for r in ok if r["plazo"] == corto), key=lambda r: r["monto"])
    print(json.dumps({"fuente": "IOL", "plazo_dias": pick["plazo"], "tasa_tna_pct": pick["tasa"],
                      "monto_usd": pick["monto"], "fecha_hora": pick["fecha_hora"],
                      "otros_plazos": [r for r in ok if r is not pick][:5],
                      "aviso": "plazo 3 = '1 día' que liquida el fin de semana" if pick["plazo"] == 3 else None},
                     indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main()
