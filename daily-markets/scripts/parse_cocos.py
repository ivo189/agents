#!/usr/bin/env python3
"""Parsea el 'Resumen de cuenta' PDF de Cocos Capital -> JSON de tenencias.
Uso: python parse_cocos.py reporte.pdf   (requiere pdftotext) | o texto ya extraído con --text archivo.txt
Toma el bloque 'POSICION AL CIERRE DEL <fecha>' más reciente. No imprime datos personales (CUIT/comitente)."""
import re, sys, json, subprocess

def num(s):
    s = s.replace("*", "").strip()
    return float(s.replace(".", "").replace(",", "."))

def main():
    if sys.argv[1] == "--text": txt = open(sys.argv[2]).read()
    else: txt = subprocess.run(["pdftotext", "-layout", sys.argv[1], "-"], capture_output=True, text=True, check=True).stdout
    blocks = re.split(r"POSICION AL CIERRE DEL (\d\d-\d\d-\d{4})", txt)
    fecha, body = blocks[-2], blocks[-1]
    pos, pend = [], ""
    num_re = r"-?[\d.]+,\d+\**"
    row = re.compile(rf"^(?P<name>.+?)\s{{2,}}(?P<qty>{num_re})\s+(?P<cur>ARS|USD MEP|USD CABLE)\s+(?P<px>{num_re}|)\s*(?P<tot>{num_re})\s+(?P<ars>{num_re})\s*$")
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith(("Cocos Capital", "RESUMEN", "Datos", "CUIT", "Nro", "Desde", "Fecha", "INSTRUMENTO", "*", "Le informamos")): continue
        if s.startswith("Total Posición"): 
            pos_total = num(s.split()[-1]); continue
        m = row.match(s)
        if m:
            name = (pend + " " + m["name"]).strip(); pend = ""
            pos.append({"instrumento": name, "ticker": (re.findall(r"\(([A-Z0-9]{3,10})\)", name) or [None])[-1],
                        "cantidad": num(m["qty"]), "moneda": m["cur"], "precio": num(m["px"]) if m["px"] else None,
                        "total_ars": num(m["ars"])})
        elif re.search(r"[A-Za-z]", s) and not re.search(num_re, s):
            pend = s
        else:
            pend = ""
    def grab(label):
        m = re.search(label + r".*?(-?[\d.]+,\d+)\s*$", body, re.M)
        return num(m.group(1)) if m else None
    pend_liq = grab(r"Posición pendiente de liquidación")
    tot = sum(p["total_ars"] for p in pos)
    for p in pos: p["peso_pct"] = round(100 * p["total_ars"] / tot, 2)
    neto = tot + (pend_liq or 0)
    apal = {"pendiente_liquidacion_ars": pend_liq, "patrimonio_neto_ars": round(neto, 2),
            "apalancamiento_bruto_sobre_neto": round(tot / neto, 2) if pend_liq and neto > 0 else None,
            "nota": "pendiente negativo = deuda por liquidar (posible caución); confirmar con Ivo"}
    print(json.dumps({"fecha_posicion": fecha, "total_ars_calculado": round(tot, 2), "apalancamiento": apal, "posiciones": pos}, indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main()
