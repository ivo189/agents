#!/usr/bin/env python3
"""Parsea PDFs 'Holdings' de Citi/HSBC (portal netxinvestor, Pershing) y el checking de Citi.
Uso: python parse_netx.py archivo.txt|archivo.pdf   -> JSON {tipo, cuenta_ult4, posiciones[{ticker,valor_usd,gl_usd}], cash_usd}
Brokerage: líneas '<TICKER>  $MV  $chg  $price ... $G/L  %'. HSBC (un solo fondo): '$MV $0.00 $price ... $G/L'. Checking: 'Available Now $X'.
No emite números de cuenta completos (solo últimos 4)."""
import re, sys, json, subprocess

def money(s): return float(s.replace("$", "").replace(",", ""))

def main():
    f = sys.argv[1]
    txt = subprocess.run(["pdftotext", "-layout", f, "-"], capture_output=True, text=True, check=True).stdout if f.endswith(".pdf") else open(f).read()
    m4 = re.search(r"(?:Checking-|\*{4,}|Holdings for [A-Z]*\d*?)(\d{4})\b", txt)
    if "Available Now" in txt:
        av = money(re.search(r"Available Now.*?(\$[\d,]+\.\d\d)", txt, re.S).group(1))
        print(json.dumps({"tipo": "checking", "cash_usd": av}, indent=1)); return
    pos = []
    row = re.compile(r"^\W*([A-Z0-9]{3,9}(?::[A-Z]{2})?)\s+(\$[\d,]+\.\d\d)\s+\$[\d,.]+\s+\$[\d.]+\s+-?\$[\d.]+\s+-?[\d.]+%\s*(-?\$[\d,]+\.\d\d)?")
    lines = txt.splitlines()
    for i, ln in enumerate(lines):
        m = row.match(ln)
        if m: pos.append({"ticker": m.group(1), "valor_usd": money(m.group(2)), "gl_usd": money(m.group(3)) if m.group(3) else None})
    if not pos:   # HSBC layout: valor en línea propia, ticker/CUSIP unas líneas antes
        cu = re.search(r"CUSIP\s+([A-Z0-9]{9})", txt) or re.search(r"\b(G\d{8}[A-Z0-9])\b", txt)
        mv = re.search(r"^\W*[A-Z0-9]{6,9}\s+(\$[\d,]+\.\d\d)\s+\$0\.00\s+\$[\d.]+\s+\$0\.00\s+0\.00%\s+(-?\$[\d,]+\.\d\d)", txt, re.M)
        if mv: pos.append({"ticker": cu.group(1) if cu else None, "valor_usd": money(mv.group(1)), "gl_usd": money(mv.group(2))})
    print(json.dumps({"tipo": "brokerage", "n": len(pos),
                      "total_usd": round(sum(p["valor_usd"] for p in pos), 2), "posiciones": pos}, indent=1))

if __name__ == "__main__":
    main()
