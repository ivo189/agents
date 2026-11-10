#!/usr/bin/env python3
"""Informe HTML de la proyección de la cuenta de Cocos (salida de proyeccion_cocos.py).
Uso: informe_proyeccion_cocos.py --var 800=a.json --var 1000=b.json --var 1200=c.json [--base 1000] [--estres 1000=r40.json] --out informe.html
Gráficos: riesgo país (3 previas), apalancamiento de Cocos, caución, neto de Cocos menos capital aportado y valuación de la cartera,
3 escenarios x 4 alternativas. 'Nada' es la referencia (gris, raya); las 3 alternativas con capital usan los slots 1-3 validados."""
import json, argparse, html

ap = argparse.ArgumentParser()
ap.add_argument("--var", action="append", required=True); ap.add_argument("--estres", action="append", default=[])
ap.add_argument("--base", default="1000"); ap.add_argument("--out", required=True)
a = ap.parse_args()
VARS = {k: json.load(open(f)) for k, f in (x.split("=", 1) for x in a.var)}
ESTR = {k: json.load(open(f)) for k, f in (x.split("=", 1) for x in a.estres)}
KEYS = list(VARS); B = VARS[a.base]; R = B["resultados"]; P = B["parametros"]
SC = ("S1", "S2", "S3"); EST = ("N", "R", "F", "A")
NOM = B["estrategias"]; CORTO = {"N": "Nada", "R": "Repagar", "F": "Fondo", "A": "AO29"}
STY = {"N": ("var(--muted)", "6 4"), "R": ("var(--s1)", ""), "F": ("var(--s2)", ""), "A": ("var(--s3)", "")}
PREV = {"800": "Previa: baja a 800", "1000": "Previa: sube a 1.000", "1200": "Previa: sube a 1.200"}
PDASH = {"800": "", "1000": "7 4", "1200": "2 3"}
MES = ["oct-26", "abr-27", "oct-27", "abr-28", "oct-28", "abr-29", "oct-29"]
MESN = ["oct-26", "nov-26", "dic-26", "ene-27", "feb-27", "mar-27", "abr-27", "may-27", "jun-27", "jul-27", "ago-27", "sep-27", "oct-27", "nov-27", "dic-27",
        "ene-28", "feb-28", "mar-28", "abr-28", "may-28", "jun-28", "jul-28", "ago-28", "sep-28", "oct-28", "nov-28", "dic-28",
        "ene-29", "feb-29", "mar-29", "abr-29", "may-29", "jun-29", "jul-29", "ago-29", "sep-29", "oct-29"]
W, H, ML, MR, MT, MB = 372, 230, 46, 62, 12, 28

def kes(v): return (f"{v/1000:,.0f}k").replace(",", ".")
def x2(v): return "neto < 0" if v is None else f"{v:.2f}x".replace(".", ",")
import math
def levmax(rr): return None if any(r["lev"] is None for r in rr) else max(r["lev"] for r in rr)
def pct(v): return f"{v:.1f} %".replace(".", ",")

def panel(pid, titulo, series, metric, ymin, ymax, labels=True):
    iw, ih = W - ML - MR, H - MT - MB; n = 36
    X = lambda m: ML + iw * m / n
    Y = lambda v: MT + ih * (1 - (v - ymin) / (ymax - ymin))
    g = ""; raw = (ymax - ymin) / 4
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 10 ** (-1 if raw >= 0.1 else -2)
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    if metric == "usd" and ymin < 0: step = min(step, 250000)
    v = math.ceil(ymin / step - 1e-9) * step
    while v <= ymax + 1e-9:
        lab = f"{v:.1f}x".replace(".", ",") if metric == "lev" else f"{v:,.0f}".replace(",", ".") if metric == "rp" else kes(v)
        g += f'<line x1="{ML}" x2="{W-MR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/><text x="{ML-6}" y="{Y(v)+3:.1f}" class="ax" text-anchor="end">{lab}</text>'
        v += step
    for i, t in enumerate(MES): g += f'<text x="{X(6*i):.1f}" y="{H-8}" class="ax" text-anchor="middle">{t}</text>'
    g += f'<line x1="{X(12):.1f}" x2="{X(12):.1f}" y1="{MT}" y2="{MT+ih}" class="ev"/><text x="{X(12)+3:.1f}" y="{MT+9}" class="ax">elección</text>'
    ends = []
    for k, label, col, dash, vals in series:
        d = ""; pen = False
        for m, val in enumerate(vals):
            if val is None: pen = False; continue
            d += f'{"L" if pen else "M"}{X(m):.1f},{Y(min(max(val, ymin), ymax)):.1f}'; pen = True
        da = f' stroke-dasharray="{dash}"' if dash else ""
        g += f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"{da}/>'
        last = next((val for val in reversed(vals) if val is not None), None)
        if last is not None: ends.append([Y(min(max(last, ymin), ymax)), k, col])
    ends.sort()
    for i in range(1, len(ends)):
        if ends[i][0] - ends[i-1][0] < 11: ends[i][0] = ends[i-1][0] + 11
    lim = MT + ih - 14                                  # que las etiquetas no pisen el eje x
    if ends and ends[-1][0] > lim:
        ends[-1][0] = lim
        for i in range(len(ends) - 2, -1, -1): ends[i][0] = min(ends[i][0], ends[i+1][0] - 11)
    if labels:
        for y, k, col in ends: g += f'<circle cx="{W-MR}" cy="{y:.1f}" r="3" fill="{col}"/><text x="{W-MR+5}" y="{y+3:.1f}" class="lab">{k}</text>'
    data = {"m": metric, "ml": ML, "iw": iw, "s": [{"l": l, "c": c, "v": v} for k, l, c, d, v in series]}
    return (f'<figure class="panel"><figcaption>{html.escape(titulo)}</figcaption><svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(titulo)}">{g}'
            f'<line class="cross" y1="{MT}" y2="{MT+ih}" x1="0" x2="0" style="display:none"/><rect class="hit" x="{ML}" y="{MT}" width="{iw}" height="{ih}" fill="transparent"/></svg>'
            f'<div class="tip" style="display:none"></div><script type="application/json">{json.dumps(data)}</script></figure>')

def serie(sc, e, key, RR=R): return [r[key] for r in RR[sc]["estrategias"][e]]
def rango(key, RR=R):
    vs = [r[key] for sc in SC for e in EST for r in RR[sc]["estrategias"][e] if r[key] is not None]; return min(vs), max(vs)
def bloque(titulo, desc, key, metric, ymin, ymax):
    h = f'<h3>{titulo}</h3><p class="desc">{desc}</p><div class="grid3">'
    for sc in SC:
        h += panel(f"{key}-{sc}", f'{sc} · {R[sc]["nombre"]}', [(CORTO[e], NOM[e], STY[e][0], STY[e][1], serie(sc, e, key)) for e in EST], metric, ymin, ymax)
    return h + "</div>"
leg = '<div class="leg">' + "".join(f'<span class="lg"><svg width="30" height="10"><line x1="0" x2="30" y1="5" y2="5" stroke="{STY[e][0]}" stroke-width="2"{(" stroke-dasharray=" + chr(34) + STY[e][1] + chr(34)) if STY[e][1] else ""}/></svg>{NOM[e]}</span>' for e in EST) + '</div>'

r0 = R["S1"]["estrategias"]["N"][0]
hoy = (f'<table><tr><th>Bonos AR</th><th>de los cuales AO29</th><th>Largos (AL35, AE38, AL41, GD46, GD29)</th><th>Notas</th><th>Efectivo / fondo</th><th>Activos</th><th>Caución</th><th>Neto</th><th>Apalancamiento</th></tr>'
       f'<tr><td class="n">{kes(r0["ar"])}</td><td class="n">{kes(r0["ao29"])}</td><td class="n">{kes(r0["largos"])}</td><td class="n">{kes(r0["notas"])}</td><td class="n">{kes(r0["fondo"])}</td><td class="n">{kes(r0["bruto"])}</td><td class="n">{kes(r0["caucion"])}</td><td class="n">{kes(r0["neto"])}</td><td class="n"><b>{x2(r0["lev"])}</b></td></tr></table>')

AP = B["aportes"]
aportes = ('<table><tr><th>Mes</th>' + "".join(f'<th>{MESN[int(m)]}</th>' for m in AP) + '<th>Total</th></tr><tr><td>Capital nuevo (USD)</td>'
           + "".join(f'<td class="n">{kes(v)}</td>' for v in AP.values()) + f'<td class="n"><b>{kes(sum(AP.values()))}</b></td></tr></table>')
alts = ('<table><tr><th>Alternativa</th><th>Capital nuevo</th><th>Flujos de la cuenta (cupones, vencimientos, ventas)</th></tr>'
        '<tr><td>Nada</td><td>No entra capital nuevo.</td><td rowspan="4">Repagan caución en todas. Si la caución ya está en cero, el excedente va al fondo USD.</td></tr>'
        f'<tr><td>Repagar caución</td><td>Se canjea cable a MEP (+{str(P["gap"]).replace(".", ",")} %) y repaga caución.</td></tr>'
        f'<tr><td>Fondo USD</td><td>Se canjea y va al fondo conservador USD de Cocos ({str(P["fondo"]).replace(".", ",")} % anual).</td></tr>'
        f'<tr><td>AO29 si RP&gt;700</td><td>Se canjea y compra AO29 a precio de mercado si el riesgo país está arriba de {int(P["umbral_ao29"])} pb; si no, va al fondo USD.</td></tr></table>')

def resumen(RR, titulo):
    t = f'<h3>{titulo}</h3><table><tr><th>Escenario</th><th>Alternativa</th><th>Capital aportado</th><th>Caución dic-27</th><th>Apal. dic-27</th><th>Apal. máximo</th><th>Neto mínimo</th><th>Neto oct-29</th><th>Neto oct-29 menos capital aportado</th><th>vs Nada</th></tr>'
    for sc in SC:
        base_ = RR[sc]["estrategias"]["N"][36]["neto_menos_aportes"]
        for i, e in enumerate(EST):
            rr = RR[sc]["estrategias"][e]; f = rr[36]
            dif = f["neto_menos_aportes"] - base_
            t += (f'<tr>{f"<td rowspan=4>{sc} · {html.escape(RR[sc]["nombre"])}</td>" if i == 0 else ""}<td style="text-align:left">{NOM[e]}</td><td class="n">{kes(f["aportes"])}</td>'
                  f'<td class="n">{kes(rr[14]["caucion"])}</td><td class="n">{x2(rr[14]["lev"])}</td><td class="n">{x2(levmax(rr[1:36]))}</td><td class="n">{kes(min(r["neto"] for r in rr[1:]))}</td>'
                  f'<td class="n">{kes(f["neto"])}</td><td class="n"><b>{kes(f["neto_menos_aportes"])}</b></td><td class="n">{"–" if e == "N" else ("+" if dif >= 0 else "") + kes(dif)}</td></tr>')
    return t + '</table>'

def flujos():
    cols = [("cupones", "Cupones cobrados"), ("venc_notas", "Vencimiento de notas"), ("venta_largos", "Venta de largos (regla 600/500/400)"), ("venc_ao29", "Vencimiento AO29"),
            ("interes_caucion", "Intereses de caución pagados"), ("compra_ao29", "Compras de AO29"), ("rend_fondo", "Rendimiento del fondo")]
    t = '<table><tr><th>Escenario</th><th>Alternativa</th>' + "".join(f'<th>{l}</th>' for _, l in cols) + '<th>Caución oct-29</th></tr>'
    for sc in SC:
        for i, e in enumerate(EST):
            f = R[sc]["estrategias"][e][36]
            t += (f'<tr>{f"<td rowspan=4>{sc}</td>" if i == 0 else ""}<td style="text-align:left">{NOM[e]}</td>' + "".join(f'<td class="n">{kes(f[k]) if f[k] else "–"}</td>' for k, _ in cols)
                  + f'<td class="n">{kes(f["caucion"])}</td></tr>')
    return t + '</table>'

def valuacion():
    hit = [(5, "mar-27"), (11, "sep-27"), (12, "oct-27"), (14, "dic-27"), (24, "oct-28"), (36, "oct-29")]
    t = '<table><tr><th>Escenario</th><th>Alternativa</th>' + "".join(f'<th colspan="4">{l}</th>' for _, l in hit) + '</tr><tr><th></th><th></th>' + '<th>Bonos AR</th><th>Fondo</th><th>Caución</th><th>Neto</th>' * len(hit) + '</tr>'
    for sc in SC:
        for i, e in enumerate(EST):
            rr = R[sc]["estrategias"][e]
            t += (f'<tr>{f"<td rowspan=4>{sc}</td>" if i == 0 else ""}<td style="text-align:left">{NOM[e]}</td>' + "".join(f'<td class="n">{kes(rr[m]["ar"])}</td><td class="n">{kes(rr[m]["fondo"])}</td><td class="n">{kes(rr[m]["caucion"])}</td><td class="n"><b>{kes(rr[m]["neto"])}</b></td>' for m, _ in hit) + '</tr>')
    return t + '</table>'

def previas():
    t = '<table><tr><th rowspan="2">Alternativa</th>' + "".join(f'<th colspan="2">{PREV[k]}</th>' for k in KEYS) + '</tr><tr>' + '<th>Neto</th><th>Apal.</th>' * len(KEYS) + '</tr>'
    for e in EST:
        t += f'<tr><td style="text-align:left">{NOM[e]}</td>' + "".join(f'<td class="n">{kes(VARS[k]["resultados"]["S1"]["estrategias"][e][11]["neto"])}</td><td class="n">{x2(VARS[k]["resultados"]["S1"]["estrategias"][e][11]["lev"])}</td>' for k in KEYS) + '</tr>'
    t += '</table><table><tr><th rowspan="2">Escenario</th><th rowspan="2">Alternativa</th>' + "".join(f'<th colspan="2">{PREV[k]}</th>' for k in KEYS) + '</tr><tr>' + '<th>Apal. máx.</th><th>Neto mínimo</th>' * len(KEYS) + '</tr>'
    for sc in SC:
        for i, e in enumerate(EST):
            t += f'<tr>{f"<td rowspan=4>{sc}</td>" if i == 0 else ""}<td style="text-align:left">{NOM[e]}</td>'
            for k in KEYS:
                rr = VARS[k]["resultados"][sc]["estrategias"][e][1:36]
                t += f'<td class="n">{x2(levmax(rr))}</td><td class="n">{kes(min(r["neto"] for r in rr))}</td>'
            t += '</tr>'
    return t + '</table>'

def estres():
    if not ESTR: return ""
    k = next(iter(ESTR)); RR = ESTR[k]["resultados"]
    t = f'<h3>Estrés de la reestructuración: canje sin recuperación</h3><p class="desc">Mismo canje (quita 25 %, cupón 5 %, 2035), pero el riesgo país se queda en 2.000 pb hasta oct-29 en lugar de bajar a 1.200. {PREV[k]}.</p><table><tr><th>Alternativa</th><th>Apal. máximo</th><th>Neto mínimo</th><th>Neto oct-29</th><th>Neto menos capital aportado</th><th>vs Nada</th></tr>'
    b_ = RR["S3"]["estrategias"]["N"][36]["neto_menos_aportes"]
    for e in EST:
        rr = RR["S3"]["estrategias"][e]; d = rr[36]["neto_menos_aportes"] - b_
        t += f'<tr><td style="text-align:left">{NOM[e]}</td><td class="n">{x2(levmax(rr[1:36]))}</td><td class="n">{kes(min(r["neto"] for r in rr[1:36]))}</td><td class="n">{kes(rr[36]["neto"])}</td><td class="n"><b>{kes(rr[36]["neto_menos_aportes"])}</b></td><td class="n">{"–" if e == "N" else ("+" if d >= 0 else "") + kes(d)}</td></tr>'
    return t + '</table>'

def lectura():
    g = lambda sc, e, RR=R: RR[sc]["estrategias"][e][36]["neto_menos_aportes"]
    d = lambda sc, e, f, RR=R: (lambda v: ("+" if v >= 0 else "") + kes(v))(g(sc, e, RR) - g(sc, f, RR))
    S3 = R["S3"]["estrategias"]; nmin = lambda e: kes(min(r["neto"] for r in S3[e][1:]))
    st = ESTR[next(iter(ESTR))]["resultados"] if ESTR else None
    li = [f'<li><b>La reestructuración es el escenario que decide.</b> Con el canje, desde la elección los bonos pasan a valer unos 25 centavos (AO29 de 82 a 25): el neto de Cocos cae a {nmin("N")} con Nada y a {nmin("A")} con AO29, es decir, <b>la cuenta no cubre la caución y en la realidad habría margin call</b> y venta forzada en el piso. Con Repagar caución el neto mínimo es {nmin("R")} y con el fondo {nmin("F")}: sobreviven, pero con apalancamiento muy alto en oct-27.</li>',
          f'<li><b>Si se paga la deuda, AO29 es la que más gana</b>: {d("S1", "A", "F")} contra el fondo con Milei y {d("S2", "A", "F")} con la oposición. <b>En la reestructuración es la que más pierde</b>: {d("S3", "A", "F")} contra el fondo' + (f' ({d("S3", "A", "F", st)} si el riesgo país no baja de 2.000)' if st else '') + '. Concentra más en el bono que ya es el 70 % de la cartera.</li>',
          f'<li><b>El fondo USD le gana a Repagar caución en resultado</b> ({d("S1", "F", "R")} con Milei, {d("S3", "F", "R")} en la reestructuración) porque rinde {str(P["fondo"]).replace(".", ",")} % contra el {str(P["caucion_tasa"]).replace(".", ",")} % de la caución; el canje lo capturan las dos. <b>Repagar caución es la más segura</b>: menor apalancamiento en todo el camino ({x2(R["S1"]["estrategias"]["R"][3]["lev"])} en ene-27 contra {x2(R["S1"]["estrategias"]["F"][3]["lev"])}) y la única que termina la reestructuración con la caución por debajo de 150 mil. El fondo es una caución cubierta: ese efectivo puede repagar en cualquier momento, por ejemplo antes de la elección.</li>',
          f'<li><b>La condición de comprar AO29 solo arriba de 700 pb no se activa</b> en ninguna previa: el capital entra entre noviembre y marzo, y en ese período el riesgo país está siempre arriba de 800.</li>',
          (lambda L: f'<li><b>La previa casi no cambia el resultado final</b>, porque en la elección los bonos se revalúan al nivel del escenario. Sí cambia el camino: en septiembre de 2027, Nada está en {x2(L("800","N"))} con la previa que baja a 800 y en {x2(L("1200","N"))} con la que sube a 1.200; Repagar caución, en {x2(L("800","R"))} y {x2(L("1200","R"))}.</li>')(lambda k, e: VARS[k]["resultados"]["S1"]["estrategias"][e][11]["lev"]) if "1200" in VARS and "800" in VARS else ""]
    return '<h3>Lectura</h3><ul>' + "".join(li) + '</ul>'

rv = [v for k in KEYS for sc in SC for v in VARS[k]["resultados"][sc]["rp_path"]]
rp_h = '<h3>Riesgo país supuesto (pb)</h3><p class="desc">Desde 938 pb (BondTerminal, 6/11/2026). Tres previas hasta septiembre de 2027; en octubre de 2027 cada escenario salta a su nivel.</p><div class="leg">' + "".join(f'<span class="lg"><svg width="30" height="10"><line x1="0" x2="30" y1="5" y2="5" stroke="var(--text)" stroke-width="2"{(" stroke-dasharray=" + chr(34) + PDASH[k] + chr(34)) if PDASH[k] else ""}/></svg>{PREV[k]}</span>' for k in KEYS) + '</div><div class="grid3">'
for sc in SC: rp_h += panel(f"rp-{sc}", f'{sc} · {R[sc]["nombre"]}', [(k, PREV[k], "var(--text)", PDASH[k], VARS[k]["resultados"][sc]["rp_path"]) for k in KEYS], "rp", 0, 2200, labels=False)
rp_h += "</div>"

lv0, lv1 = rango("lev"); nm0, nm1 = rango("neto_menos_aportes"); n0, n1 = rango("neto")
body = (rp_h + leg
        + bloque("Apalancamiento de Cocos (activos / neto)", "1,0x = sin caución. El salto de octubre de 2027 es la elección: los bonos se revalúan al nivel de riesgo país del escenario. Eje recortado en 5x; la línea se corta cuando el neto es negativo.", "lev", "lev", 1.0, min(round(lv1 + 0.2, 1), 5.0))
        + bloque("Caución (USD)", "Lo que queda por devolver. Baja con el capital nuevo (solo en Repagar), los cupones, los vencimientos y la venta escalonada de largos.", "caucion", "usd", 0, 500000)
        + bloque("Patrimonio neto de Cocos (activos a precio de mercado − caución, USD)", "Lo que te queda si vendés todo y devolvés la caución. Incluye el capital aportado. Por debajo de cero, la cuenta no cubre la caución: en la realidad habría margin call (el modelo no lo simula).", "neto", "usd", math.floor(n0 / 100000) * 100000, round(n1 / 100000 + 1) * 100000)
        + bloque("Neto de Cocos menos capital aportado (USD)", "La medida justa para comparar: descuenta los 130 mil que entran en las tres alternativas con capital. La distancia a Nada es lo que ganó (o perdió) ese capital.", "neto_menos_aportes", "usd", math.floor(nm0 / 100000) * 100000, round(nm1 / 100000 + 1) * 100000))

page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Proyección de Cocos</title>
<style>
:root{{--bg:#fcfcfb;--text:#0b0b0b;--muted:#52514e;--grid:#e6e5e1;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--card:#fff;--line:#d6d5d0}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--card:#222220;--line:#3d3c38}}}}
:root[data-theme=dark]{{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--card:#222220;--line:#3d3c38}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Arial,Helvetica,sans-serif;padding:16px}}main{{max-width:1100px;margin:0 auto}}
h1{{font-size:20px;margin:0 0 4px}}h3{{margin:26px 0 2px;font-size:16px}}.desc{{color:var(--muted);margin:0 0 8px}}
.grid3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
.panel{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px;position:relative}}figcaption{{font-weight:bold;font-size:12px;margin:0 0 2px}}
svg{{width:100%;height:auto;display:block}}.grid{{stroke:var(--grid);stroke-width:1}}.ax{{fill:var(--muted);font-size:10px}}.lab{{font-size:11px;font-weight:bold;fill:var(--text)}}.ev{{stroke:var(--muted);stroke-dasharray:2 3;stroke-width:1}}.cross{{stroke:var(--muted);stroke-width:1}}
.tip{{position:absolute;top:30px;left:50px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;pointer-events:none;white-space:nowrap}}
.leg{{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0}}.lg{{display:inline-flex;align-items:center;gap:6px;font-size:12px;white-space:nowrap}}
table{{border-collapse:collapse;font-size:12px;margin:8px 0;display:block;overflow-x:auto}}th,td{{border:1px solid var(--line);padding:4px 6px;text-align:center}}th{{background:var(--grid)}}td.n{{text-align:right;font-variant-numeric:tabular-nums}}
details{{margin-top:14px}}.foot{{color:var(--muted);font-size:12px;margin-top:18px}}
</style></head><body><main>
<h1>Cocos · escenarios y alternativas de caución · nov-2026 a oct-2029</h1>
<p class="desc">Solo la cuenta de Cocos. 3 escenarios electorales × 3 previas de riesgo país × 4 alternativas para el capital nuevo. Gráficos con la previa “{PREV[a.base].split(": ")[1]}”; las otras previas están en las tablas de abajo.</p>
<h3>Dónde arrancás</h3><p class="desc">Posiciones del estado de Cocos del 31/10 a precios de BondTerminal del 6/11/2026 (MEP), riesgo país 938 pb.</p>{hoy}
<h3>Premisas</h3><p class="desc">Capital nuevo (fin de mes), igual en las tres alternativas con capital:</p>{aportes}{alts}
<p class="desc">Escenarios desde la elección (oct-2027): <b>S1 Milei reelecto</b>, riesgo país a {int(P["s1"])} pb. <b>S2 Oposición con shock</b>, {int(P["s2_peak"])} pb por {P["s2_hold"]} meses y baja a {int(P["s2_end"])} pb en oct-2029 (paga). <b>S3 Reestructuración (canje)</b>: 2.000 pb en la elección, default en dic-2027 (sin cupones), canje en jun-2028 de todos los soberanos por un bono nuevo con quita del {int(P["quita"])} % del nominal, cupón {str(P["cupon_nuevo"]).replace(".", ",")} % semestral y vencimiento 2035; el riesgo país baja de 2.000 (jun-28) a {int(P["s3_end"])} pb (oct-29). Desde la elección, cada bono vale el {100-int(P["quita"])} % del precio del bono nuevo a TIR UST + riesgo país (referencia: en el default de 2020, los bonos cotizaron en la zona de 20 a 35 centavos). En todas las alternativas rige la venta escalonada de largos (600 pb vende 25 %, 500 pb llega a 50 %, 400 pb a 100 %) y lo producido repaga caución: solo se activa en S1.</p>
{resumen(R, "Resultado por escenario y alternativa")}
{lectura()}
{body}
<h3>Flujos acumulados nov-26 a oct-29 (USD)</h3><p class="desc">Lo que entró y salió de la cuenta, aparte del capital nuevo.</p>{flujos()}
<h3>Valuación de la cartera por hito (USD)</h3>{valuacion()}
<h3>Previas: valuación en septiembre de 2027 (antes de la elección) y riesgo en el camino</h3><p class="desc">Antes de la elección los tres escenarios son iguales, así que la primera tabla no depende del escenario.</p>{previas()}
{estres()}
<p class="foot">Supuestos: AO29 con cupón 6 % pagado 0,5 % por mes y capital al vencimiento (oct-29); resto de soberanos como bonos sintéticos calibrados a precio y duration de BondTerminal, cupón semestral (ene/jul); TIR = UST + spread proporcional al riesgo país. Notas de Cocos (70 mil) con cupones y capital al par. Caución USD {str(P["caucion_tasa"]).replace(".", ",")} % anual; fondo USD {str(P["fondo"]).replace(".", ",")} %; captura del canje cable a MEP {str(P["gap"]).replace(".", ",")} % neta. Sin margin call ni ventas forzadas. Modelo de escenarios, no predicción; no es asesoramiento financiero.</p>
</main>
<script>
document.querySelectorAll('figure.panel').forEach(function(f){{
  var d=JSON.parse(f.querySelector('script').textContent),svg=f.querySelector('svg'),hit=f.querySelector('.hit'),cr=f.querySelector('.cross'),tip=f.querySelector('.tip');
  var M={json.dumps(MESN)},n=d.s[0].v.length;
  function f2(v){{if(v===null)return 'n/d';if(d.m==='rp')return Math.round(v)+' pb';if(d.m==='lev')return v.toFixed(2).replace('.',',')+'x';return 'USD '+Math.round(v/1000).toLocaleString('es-AR')+' mil';}}
  hit.addEventListener('mousemove',function(e){{var r=svg.getBoundingClientRect(),sc=r.width/svg.viewBox.baseVal.width,x=(e.clientX-r.left)/sc;var i=Math.max(0,Math.min(n-1,Math.round((x-d.ml)/d.iw*(n-1))));var px=d.ml+d.iw*i/(n-1);cr.setAttribute('x1',px);cr.setAttribute('x2',px);cr.style.display='';
    tip.innerHTML='<b>'+M[i]+(i===0?' (hoy)':'')+'</b><br>'+d.s.map(function(s){{return '<span style="color:'+s.c+'">●</span> '+s.l+': '+f2(s.v[i]);}}).join('<br>');tip.style.display='';tip.style.left=Math.min(r.width-200,Math.max(4,px*sc+8))+'px';}});
  hit.addEventListener('mouseleave',function(){{cr.style.display='none';tip.style.display='none';}});
}});
</script></body></html>'''
open(a.out, "w").write(page)
print("ok", len(page))
