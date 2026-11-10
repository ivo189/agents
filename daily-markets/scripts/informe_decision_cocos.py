#!/usr/bin/env python3
"""Informe de decisión para la cuenta de Cocos: cómo administrar una cartera de bonos AR comprada a paridades más altas, con caución.
Plantea la decisión en dos niveles: (1) poner o no capital nuevo (hasta 130 mil entre nov-26 y mar-27) y (2) si se pone, dónde.
Lee las salidas JSON de proyeccion_cocos.py (base y sensibilidades): narrativa, tablas, gráfico de resultados y proyecciones temporales.
Uso: informe_decision_cocos.py --dir <carpeta con pc_800/1000/1200.json, pc_1000_sinrec.json, pc_1000_cau2.json, pc_1000_sinregla.json> --out informe.html
Sin margin call: si el neto de Cocos queda negativo, Ivo inyecta USD para cubrir el margen (se informa cuánto)."""
import json, argparse, os, sys, html, math, importlib.util

ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--tbill", type=float, default=4.1, help="tasa de T-bills para el capital que queda afuera en 'Nada'")
ap.add_argument("--compra-ao29", type=float, default=95.0, help="precio de compra del AO29 (Ivo)")
a = ap.parse_args()
L = lambda f: json.load(open(os.path.join(a.dir, f)))
B = L("pc_1000.json"); R = B["resultados"]; P = B["parametros"]; APO = {int(k): v for k, v in B["aportes"].items()}
V = {k: L(f"pc_{k}.json")["resultados"] for k in ("800", "1000", "1200")}
SR, C2, SG = L("pc_1000_sinrec.json")["resultados"], L("pc_1000_cau2.json")["resultados"], L("pc_1000_sinregla.json")["resultados"]
argv, sys.argv = sys.argv, [sys.argv[0]]
sp = importlib.util.spec_from_file_location("pc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "proyeccion_cocos.py"))
pc = importlib.util.module_from_spec(sp); sp.loader.exec_module(pc); sys.argv = argv
ESC = pc.escenarios()

SC = ("S1", "S2", "S3"); BASE4 = ("N", "R", "F", "A"); ALL = ("N", "T", "R", "F", "A", "M", "P")
NOM = dict(B["estrategias"]); NOM["T"] = "Nada, con los 130 mil en T-bills afuera"
CORTO = {"N": "Nada", "T": "Nada + T-bills afuera", "R": "Repagar caución", "F": "Fondo USD", "A": "AO29 si RP>700", "M": "Mitad fondo / AO29", "P": "Fondo → repago sep-27"}
SCN = {"S1": "Milei reelecto", "S2": "Oposición con shock", "S3": "Reestructuración (canje)"}
STY = {"N": ("var(--muted)", "6 4"), "R": ("var(--s1)", ""), "F": ("var(--s2)", ""), "A": ("var(--s3)", "")}
MESN = ["oct-26", "nov-26", "dic-26", "ene-27", "feb-27", "mar-27", "abr-27", "may-27", "jun-27", "jul-27", "ago-27", "sep-27", "oct-27", "nov-27", "dic-27",
        "ene-28", "feb-28", "mar-28", "abr-28", "may-28", "jun-28", "jul-28", "ago-28", "sep-28", "oct-28", "nov-28", "dic-28",
        "ene-29", "feb-29", "mar-29", "abr-29", "may-29", "jun-29", "jul-29", "ago-29", "sep-29", "oct-29"]

def k_(v): return f"{v/1000:,.0f}k".replace(",", ".")
def sk(v): return ("+" if v >= 0 else "−") + k_(abs(v))
def x2(v): return "neto < 0" if v is None else "más de 50x" if v > 50 else f"{v:.2f}x".replace(".", ",")
def c1(v): return f"{v:.1f}".replace(".", ",")

# 'Nada' con el capital afuera: los 130 mil quedan en T-bills (sin canje) hasta oct-29
TB = sum(v * (1 + a.tbill / 100) ** ((36 - m) / 12) for m, v in APO.items()) - sum(APO.values())
def fin(RR, s, e):
    if e == "T": return RR[s]["estrategias"]["N"][36]["neto_menos_aportes"] + TB
    return RR[s]["estrategias"][e][36]["neto_menos_aportes"]
def row(s, e, m, RR=R): return RR[s]["estrategias"]["N" if e == "T" else e][m]
def nmin(s, e, RR=R): return min(r["neto"] for r in RR[s]["estrategias"]["N" if e == "T" else e][1:])
def cobertura(s, e, L_=3.0, RR=R):
    w = min(RR[s]["estrategias"]["N" if e == "T" else e][1:], key=lambda r: r["neto"])
    return w["fecha"], max(0, -w["neto"]), max(0, round((w["bruto"] - w["fondo"]) / L_ - w["neto"]))
def be(e, f="F", RR=R):
    up = (fin(RR, "S1", e) - fin(RR, "S1", f) + fin(RR, "S2", e) - fin(RR, "S2", f)) / 2
    dn = fin(RR, "S3", f) - fin(RR, "S3", e)
    return None if dn <= 0 or up <= 0 else 100 * up / (up + dn)
d = lambda s, e, f, RR=R: fin(RR, s, e) - fin(RR, s, f)

# cartera de hoy
VAL = {k: vn * p / 100 for k, (vn, p, y, du) in pc.BONOS.items()}; VT = sum(VAL.values())
TIR = sum(VAL[k] * pc.BONOS[k][2] for k in VAL) / VT; DUR = sum(VAL[k] * pc.BONOS[k][3] for k in VAL) / VT
DEV = VT * TIR / 100; CAU_COSTO = pc.CAUCION0 * P["caucion_tasa"] / 100; DV100 = VT * DUR / 100
P_AO = pc.BONOS["AO29"][1]; PERD_AO = pc.BONOS["AO29"][0] * (a.compra_ao29 - P_AO) / 100

# ---------- gráficos ----------
W, H, ML, MR, MT, MB = 372, 230, 46, 62, 12, 28
def panel(titulo, series, metric, ymin, ymax, labels=True):
    iw, ih = W - ML - MR, H - MT - MB; n = 36
    X = lambda m: ML + iw * m / n
    Y = lambda v: MT + ih * (1 - (v - ymin) / (ymax - ymin))
    g = ""; raw = (ymax - ymin) / 4
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 10 ** (-1 if raw >= 0.1 else -2)
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    if metric == "usd" and ymin < 0: step = min(step, 250000)
    v = math.ceil(ymin / step - 1e-9) * step
    while v <= ymax + 1e-9:
        lab = f"{v:.1f}x".replace(".", ",") if metric == "lev" else f"{v:,.0f}".replace(",", ".") if metric == "rp" else k_(v)
        g += f'<line x1="{ML}" x2="{W-MR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/><text x="{ML-6}" y="{Y(v)+3:.1f}" class="ax" text-anchor="end">{lab}</text>'
        v += step
    for i, t in enumerate(("oct-26", "abr-27", "oct-27", "abr-28", "oct-28", "abr-29", "oct-29")): g += f'<text x="{X(6*i):.1f}" y="{H-8}" class="ax" text-anchor="middle">{t}</text>'
    g += f'<line x1="{X(12):.1f}" x2="{X(12):.1f}" y1="{MT}" y2="{MT+ih}" class="ev"/><text x="{X(12)+3:.1f}" y="{MT+9}" class="ax">elección</text>'
    ends = []
    for k, label, col, dash, vals in series:
        dd = ""; pen = False
        for m, val in enumerate(vals):
            if val is None: pen = False; continue
            dd += f'{"L" if pen else "M"}{X(m):.1f},{Y(min(max(val, ymin), ymax)):.1f}'; pen = True
        da = f' stroke-dasharray="{dash}"' if dash else ""
        g += f'<path d="{dd}" fill="none" stroke="{col}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"{da}/>'
        last = next((val for val in reversed(vals) if val is not None), None)
        if last is not None: ends.append([Y(min(max(last, ymin), ymax)), k, col])
    ends.sort()
    for i in range(1, len(ends)):
        if ends[i][0] - ends[i-1][0] < 11: ends[i][0] = ends[i-1][0] + 11
    lim = MT + ih - 14
    if ends and ends[-1][0] > lim:
        ends[-1][0] = lim
        for i in range(len(ends) - 2, -1, -1): ends[i][0] = min(ends[i][0], ends[i+1][0] - 11)
    if labels:
        for y, k, col in ends: g += f'<circle cx="{W-MR}" cy="{y:.1f}" r="3" fill="{col}"/><text x="{W-MR+5}" y="{y+3:.1f}" class="lab">{k}</text>'
    data = {"m": metric, "ml": ML, "iw": iw, "s": [{"l": l, "c": c, "v": v} for k, l, c, dd, v in series]}
    return (f'<figure class="panel tl"><figcaption>{html.escape(titulo)}</figcaption><svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(titulo)}">{g}'
            f'<line class="cross" y1="{MT}" y2="{MT+ih}" x1="0" x2="0" style="display:none"/><rect class="hit" x="{ML}" y="{MT}" width="{iw}" height="{ih}" fill="transparent"/></svg>'
            f'<div class="tip" style="display:none"></div><script type="application/json">{json.dumps(data)}</script></figure>')
def serie(s, e, key): return [r[key] for r in R[s]["estrategias"][e]]
def rango(key):
    vs = [r[key] for s in SC for e in BASE4 for r in R[s]["estrategias"][e] if r[key] is not None]; return min(vs), max(vs)
SHORT = {"N": "Nada", "R": "Repagar", "F": "Fondo", "A": "AO29"}
def bloque(titulo, desc, key, metric, ymin, ymax):
    h = f'<h4>{titulo}</h4><p class="desc">{desc}</p><div class="grid3">'
    for s in SC: h += panel(f'{SCN[s]}', [(SHORT[e], NOM[e], STY[e][0], STY[e][1], serie(s, e, key)) for e in BASE4], metric, ymin, ymax)
    return h + "</div>"
leg = '<div class="leg">' + "".join(f'<span class="lg"><svg width="30" height="10"><line x1="0" x2="30" y1="5" y2="5" stroke="{STY[e][0]}" stroke-width="2"{(" stroke-dasharray=" + chr(34) + STY[e][1] + chr(34)) if STY[e][1] else ""}/></svg>{NOM[e]}</span>' for e in BASE4) + '</div>'

def barras(ests, titulo):
    vals = [fin(R, s, e) for s in SC for e in ests]; hi = max(vals); lo = min(0, min(vals))
    Wb, rowh, lab, pad = 340, 24, 150, 54
    h = f'<figure class="panel"><figcaption>{titulo}</figcaption><div class="grid3">'
    for s in SC:
        Hb = rowh * len(ests) + 12; iw = Wb - lab - pad
        X = lambda v: lab + iw * (v - lo) / (hi - lo)
        g = f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="4" y2="{Hb-6}" class="axis"/>'
        best = max(ests, key=lambda e: fin(R, s, e))
        for i, e in enumerate(ests):
            v = fin(R, s, e); y = 6 + i * rowh; x0, x1 = sorted((X(0), X(v)))
            g += (f'<text x="{lab-6}" y="{y+13}" class="ax" text-anchor="end">{html.escape(CORTO[e])}</text>'
                  f'<rect x="{x0:.1f}" y="{y+2}" width="{max(x1-x0,1):.1f}" height="{rowh-8}" rx="3" fill="{"var(--s1)" if e == best else "var(--bar)"}"><title>{html.escape(NOM[e])}: USD {k_(v)}</title></rect>'
                  f'<text x="{x1+4:.1f}" y="{y+13}" class="val">{k_(v)}</text>')
        h += f'<div><div class="sub">{SCN[s]}</div><svg viewBox="0 0 {Wb} {Hb}" role="img" aria-label="{SCN[s]}">{g}</svg></div>'
    return h + '</div><p class="note">En azul, la mejor de cada escenario. Neto de Cocos en oct-29 menos el capital aportado; en “Nada + T-bills afuera” se suma lo que ganan los 130 mil afuera.</p></figure>'

# ---------- tablas ----------
def t_precios():
    hit = [(0, "hoy"), (5, "mar-27"), (11, "sep-27"), (12, "oct-27"), (20, "jun-28"), (36, "oct-29")]
    t = '<table><tr><th>Escenario</th><th>Bono</th>' + "".join(f"<th>{l}</th>" for _, l in hit) + '</tr>'
    for s in SC:
        for i, b in enumerate(("AO29", "AL35")):
            t += f'<tr>{f"<td rowspan=2 class=l>{SCN[s]}</td>" if i == 0 else ""}<td>{b}</td>' + "".join(f'<td class="n">{c1(pc.px(b, m, ESC[s]))}</td>' for m, _ in hit) + '</tr>'
    return t + '</table><p class="note">Precio por 100 de nominal. En la reestructuración, desde la elección el precio es el del paquete del canje (75 % del bono nuevo); en jun-28 se canjea.</p>'

def t_matriz(ests):
    t = '<table><tr><th>Alternativa</th>' + "".join(f'<th>{SCN[s]}</th>' for s in SC) + '<th>Promedio simple</th><th>Peor caso</th><th>Distancia mejor-peor</th></tr>'
    for e in ests:
        v = [fin(R, s, e) for s in SC]
        t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{k_(x)}</td>' for x in v) + f'<td class="n">{k_(sum(v)/3)}</td><td class="n">{k_(min(v))}</td><td class="n">{k_(max(v)-min(v))}</td></tr>'
    return t + '</table>'

def t_camino(ests):
    cols = [("Apal. mar-27", lambda e: x2(row("S1", e, 5)["lev"])), ("Capacidad de compra a 2x, mar-27", lambda e: k_(row("S1", e, 5)["capacidad_2x"])),
            ("Caución sep-27", lambda e: k_(row("S1", e, 11)["caucion"])), ("Apal. sep-27", lambda e: x2(row("S1", e, 11)["lev"])),
            ("Fondo en Cocos, sep-27", lambda e: k_(row("S1", e, 11)["fondo"])), ("AO29 / activos de Cocos, mar-27", lambda e: f'{100*row("S1", e, 5)["ao29"]/row("S1", e, 5)["bruto"]:.0f} %')]
    t = '<table><tr><th>Alternativa</th>' + "".join(f"<th>{c}</th>" for c, _ in cols) + '</tr>'
    for e in ests: t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{fn(e)}</td>' for _, fn in cols) + '</tr>'
    return t + '</table><p class="note">Antes de la elección los tres escenarios son iguales.</p>'

def t_s3(ests):
    t = '<table><tr><th>Alternativa</th><th>Neto oct-27 (peor mes)</th><th>Apal. oct-27</th><th>Inyección para neto ≥ 0</th><th>Inyección para volver a 3x (usando antes el fondo)</th><th>Neto oct-29</th><th>Caución oct-29</th><th>Si el riesgo país no baja de 2.000: neto − aportes</th></tr>'
    for e in ests:
        f_, n0, n3 = cobertura("S3", e)
        t += (f'<tr><td class="l">{NOM[e]}</td><td class="n">{k_(nmin("S3", e))}</td><td class="n">{x2(row("S3", e, 12)["lev"])}</td><td class="n">{k_(n0) if n0 else "–"}</td>'
              f'<td class="n"><b>{k_(n3)}</b></td><td class="n">{k_(row("S3", e, 36)["neto"])}</td><td class="n">{k_(row("S3", e, 36)["caucion"])}</td><td class="n">{k_(fin(SR, "S3", e))}</td></tr>')
    return t + '</table><p class="note">La inyección no cambia el resultado económico: es capital que entra y repaga caución. Lo que cambia es cuánto tenés que tener disponible en oct-27. 3x es una referencia; tu acuerdo de margen con Cocos puede ser otro. En “Nada + T-bills afuera”, los 130 mil (más intereses) ya están disponibles para esa cobertura.</p>'

def t_valuacion():
    hit = [(5, "mar-27"), (11, "sep-27"), (12, "oct-27"), (14, "dic-27"), (24, "oct-28"), (36, "oct-29")]
    t = '<table><tr><th>Escenario</th><th>Alternativa</th>' + "".join(f'<th colspan="4">{l}</th>' for _, l in hit) + '</tr><tr><th></th><th></th>' + '<th>Bonos AR</th><th>Fondo</th><th>Caución</th><th>Neto</th>' * len(hit) + '</tr>'
    for s in SC:
        for i, e in enumerate(BASE4):
            rr = R[s]["estrategias"][e]
            t += f'<tr>{f"<td rowspan=4>{s}</td>" if i == 0 else ""}<td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{k_(rr[m]["ar"])}</td><td class="n">{k_(rr[m]["fondo"])}</td><td class="n">{k_(rr[m]["caucion"])}</td><td class="n"><b>{k_(rr[m]["neto"])}</b></td>' for m, _ in hit) + '</tr>'
    return t + '</table>'

def t_flujos():
    cols = [("cupones", "Cupones cobrados"), ("venc_notas", "Vencimiento de notas"), ("venta_largos", "Venta de largos"), ("venc_ao29", "Vencimiento AO29"),
            ("interes_caucion", "Intereses de caución"), ("compra_ao29", "Compras de AO29"), ("rend_fondo", "Rendimiento del fondo")]
    t = '<table><tr><th>Escenario</th><th>Alternativa</th>' + "".join(f'<th>{l}</th>' for _, l in cols) + '<th>Caución oct-29</th></tr>'
    for s in SC:
        for i, e in enumerate(BASE4):
            f = R[s]["estrategias"][e][36]
            t += f'<tr>{f"<td rowspan=4>{s}</td>" if i == 0 else ""}<td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{k_(f[k]) if f[k] else "–"}</td>' for k, _ in cols) + f'<td class="n">{k_(f["caucion"])}</td></tr>'
    return t + '</table>'

def t_sens(ests):
    rows_ = [("Base (caución 0,5 %, previa 1.000)", R), ("Caución a 2 %", C2), ("Sin la regla de venta de largos", SG), ("Reestructuración sin recuperación (RP 2.000)", SR)]
    t = '<table><tr><th>Sensibilidad</th><th>Escenario</th>' + "".join(f'<th>{CORTO[e]}</th>' for e in ests) + '</tr>'
    for nombre, RR in rows_:
        for i, s in enumerate(SC):
            best = max(ests, key=lambda e: fin(RR, s, e))
            t += f'<tr>{f"<td rowspan=3 class=l>{nombre}</td>" if i == 0 else ""}<td class="l">{SCN[s]}</td>' + "".join(f'<td class="n">{"<b>" if e == best else ""}{k_(fin(RR, s, e))}{"</b>" if e == best else ""}</td>' for e in ests) + '</tr>'
    return t + '</table><p class="note">Neto oct-29 menos capital aportado. En negrita, la mejor de cada fila.</p>'

def t_previa(ests):
    t = '<table><tr><th>Alternativa</th>' + "".join(f'<th>Apal. sep-27, previa {k}</th>' for k in V) + "".join(f'<th>Neto − aportes en reestructuración, previa {k}</th>' for k in V) + '</tr>'
    for e in ests:
        t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{x2(row("S1", e, 11, V[k])["lev"])}</td>' for k in V) + "".join(f'<td class="n">{k_(fin(V[k], "S3", e))}</td>' for k in V) + '</tr>'
    return t + '</table>'

# ---------- texto ----------
bA, bM, bAs = be("A"), be("M"), be("A", RR=SR)
cob = {e: cobertura("S3", e)[2] for e in ALL}
salto = pc.px("AO29", 12, ESC["S1"]) - pc.px("AO29", 11, ESC["S1"])
r0 = row("S1", "N", 0)

proposito = f'''<p><b>Para qué es este análisis.</b> La cartera de Cocos quedó invertida en bonos argentinos comprados a paridades más altas que las actuales (por ejemplo, el AO29 se compró a {c1(a.compra_ao29)} y hoy cotiza a {c1(P_AO)}: unos {k_(PERD_AO)} de pérdida no realizada solo en ese bono) y está financiada con caución. El devengamiento juega a favor: la cartera rinde una TIR promedio de {c1(TIR)} % (unos {k_(DEV)} por año sobre el valor de mercado) contra una caución de {c1(P["caucion_tasa"])} % ({k_(CAU_COSTO)} por año). Pero la sensibilidad al riesgo político es alta: con una duration de {c1(DUR)}, cada 100 pb de suba del riesgo país le saca unos {k_(DV100)} al valor de la cartera, y la elección de octubre de 2027 abre futuros muy distintos.</p>
<p>El objetivo es ayudarte a decidir cómo administrar esa cartera hasta oct-29, cuando vence el AO29. La decisión tiene dos niveles:</p>
<ol><li><b>Poner o no capital nuevo.</b> Una posibilidad es no hacer nada y dejar que el devengamiento y los cupones vayan bajando la caución. La otra es aportar hasta 130 mil entre nov-26 y mar-27 (15 + 15 + 70 + 15 + 15).</li>
<li><b>Si se pone, dónde:</b> repagar caución, un fondo USD dentro de Cocos, o más AO29.</li></ol>
<p>Para cada combinación se proyecta la cartera mes a mes en tres escenarios electorales y tres caminos de riesgo país antes de la elección.</p>'''

resumen = f'''<ul class="key">
<li><b>No hacer nada es viable si se paga la deuda, pero deja la cartera expuesta.</b> Con Milei o con la oposición, Nada termina unos {k_(-(d("S1","N","F")+d("S2","N","F"))/2)} debajo del fondo, y si los 130 mil quedan afuera en T-bills la diferencia baja a {k_(-d("S1","T","F"))}. El costo es el camino: apalancamiento de {x2(row("S1","N",11)["lev"])} en la previa y, en una reestructuración, neto de Cocos de {k_(nmin("S3","N"))} y {k_(cob["N"])} para cubrir el margen.</li>
<li><b>Si ponés capital, la decisión es una apuesta a la elección de oct-27.</b> AO29 deja {sk(d("S1","A","F"))} contra el fondo si se paga y {sk(d("S3","A","F"))} si hay reestructuración. AO29 conviene solo si la probabilidad de reestructuración es menor a <b>{bA:.0f} %</b> ({bAs:.0f} % si después del canje el riesgo país no baja).</li>
<li><b>El fondo USD le gana a repagar caución en los tres escenarios</b> ({sk(d("S1","F","R"))}, {sk(d("S2","F","R"))}, {sk(d("S3","F","R"))}): rinde {c1(P["fondo"])} % contra {c1(P["caucion_tasa"])} % y el canje lo capturan los dos. Como cubrís el margen con dólares de afuera, repagar solo compra menor apalancamiento.</li>
<li><b>El fondo es la alternativa más flexible y la mejor en la reestructuración</b>: deja la decisión abierta hasta septiembre de 2027 y es la que menos cobertura necesita ({k_(cob["F"])}). Su límite: si gana Milei, el AO29 salta {c1(salto)} puntos en el mes de la elección, y esa suba solo la captura quien ya está comprado.</li>
</ul>'''

esc_txt = f'''
<div class="card"><h4>Milei reelecto</h4><p>El riesgo país pasa de ~1.000 a <b>{int(P["s1"])} pb</b> en oct-27. El AO29 sube de {c1(pc.px("AO29",11,ESC["S1"]))} a {c1(pc.px("AO29",12,ESC["S1"]))} y los largos de ~64 a ~90. Se cumplen los tres escalones de la regla (600/500/400 pb) y se venden todos los largos por unos {k_(row("S1","N",36)["venta_largos"])}, que repagan caución. El AO29 vence en oct-29 y la caución termina en cero.</p>
<p><b>Qué decide el resultado:</b> cuánto AO29 tenías antes de la elección. Cada 100 mil en AO29 comprados en el verano terminan unos {k_(d("S1","A","F")/row("S1","A",36)["compra_ao29"]*100000)} arriba del fondo.</p></div>
<div class="card"><h4>Oposición con shock</h4><p>El riesgo país salta a <b>{int(P["s2_peak"])} pb</b> por {P["s2_hold"]} meses y baja a {int(P["s2_end"])} en oct-29; la deuda se paga. El AO29 cae a {c1(pc.px("AO29",12,ESC["S2"]))}, pero al ser corto vuelve a 100 al vencer. Los largos caen a ~51 y terminan en ~{c1(pc.px("AL35",36,ESC["S2"]))}. No se activa la regla de venta.</p>
<p><b>Qué decide el resultado:</b> como en Milei, el AO29 gana porque vence a la par; el shock pesa en el camino (apalancamiento de Cocos en oct-27: {x2(row("S2","N",12)["lev"])} con Nada, {x2(row("S2","F",12)["lev"])} con el fondo, {x2(row("S2","R",12)["lev"])} repagando).</p></div>
<div class="card"><h4>Reestructuración (canje)</h4><p>Riesgo país a 2.000 pb en oct-27, default en dic-27, canje en jun-28 por un bono nuevo con quita del {int(P["quita"])} % del nominal, cupón {c1(P["cupon_nuevo"])} % y vencimiento 2035. Desde la elección cada bono vale unos {c1(pc.px("AO29",12,ESC["S3"]))} centavos y sube a {c1(pc.px("AO29",36,ESC["S3"]))} en oct-29 a medida que el riesgo país baja a {int(P["s3_end"])} pb y vuelven los cupones.</p>
<p><b>Qué decide el resultado:</b> cuánto expuesto a bonos AR estás el día de la elección. La cartera pierde ~{k_(row("S3","N",11)["ar"]-row("S3","N",12)["ar"])} en un mes; con Nada y con AO29 el neto de Cocos queda negativo y hay que cubrir el margen.</p></div>'''

alt_txt = f'''<table><tr><th>Alternativa</th><th>Qué hace</th><th>A favor</th><th>En contra</th></tr>
<tr><td class="l">Nada</td><td>No entra capital; cupones y vencimientos van bajando la caución.</td><td>No compromete dólares nuevos en Argentina. Los 130 mil pueden quedar afuera rindiendo ({k_(TB)} en T-bills a oct-29) y disponibles para cubrir margen. Si se paga la deuda, termina cerca de las otras.</td><td>Apalancamiento alto todo el camino ({x2(row("S1","N",11)["lev"])} en sep-27) y sin capacidad de compra. En la reestructuración el neto de Cocos va a {k_(nmin("S3","N"))} y necesitás {k_(cob["N"])} para volver a 3x.</td></tr>
<tr><td class="l">Repagar caución</td><td>Canje (+{c1(P["gap"])} %) y repago.</td><td>El menor apalancamiento y la mayor capacidad de compra a 2x ({k_(row("S1","R",5)["capacidad_2x"])} en mar-27). Menos cobertura en la reestructuración ({k_(cob["R"])}).</td><td>La que menos rinde de las que ponen capital: la plata gana el {c1(P["caucion_tasa"])} % de la caución. No se deshace.</td></tr>
<tr><td class="l">Fondo USD</td><td>Canje y fondo conservador de Cocos ({c1(P["fondo"])} %).</td><td>La mejor en la reestructuración y la que menos cobertura necesita ({k_(cob["F"])}). Líquida: puede repagar caución o comprar bonos cuando quieras. Baja la concentración en AO29.</td><td>Apalancamiento contable más alto que repagar ({x2(row("S1","F",11)["lev"])} en sep-27). Deja pasar la suba de la elección si gana Milei.</td></tr>
<tr><td class="l">AO29 si RP&gt;700</td><td>Canje y compra de AO29.</td><td>La mejor si se paga ({sk(d("S1","A","F"))} contra el fondo). TIR ~{c1(pc.BONOS["AO29"][2])} % y cupón mensual que repaga caución.</td><td>La peor en la reestructuración ({sk(d("S3","A","F"))} contra el fondo). AO29 llega al {100*row("S1","A",5)["ao29"]/row("S1","A",5)["bruto"]:.0f} % de los activos de Cocos; necesita {k_(cob["A"])} de cobertura.</td></tr>
<tr><td class="l">Mitad fondo, mitad AO29 <span class="tag">variante</span></td><td>65 mil a cada uno.</td><td>Captura la mitad de la suba si se paga y conserva liquidez.</td><td>Pierde la mitad en la reestructuración; necesita {k_(cob["M"])} de cobertura.</td></tr>
<tr><td class="l">Fondo → repago en sep-27 <span class="tag">variante</span></td><td>Fondo hasta sep-27; ahí repaga caución.</td><td>Le gana a repagar desde el principio en los tres escenarios ({sk(d("S1","P","R"))}) con la misma protección en la elección.</td><td>Pierde contra quedarse en el fondo ({sk(d("S3","P","F"))} en la reestructuración): si cubrís margen con dólares de afuera, repagar no agrega valor.</td></tr>
</table>'''

trade = f'''
<h4>1. Poner capital o no</h4>
<p>Si se paga la deuda, el capital nuevo agrega poco: contra Nada con los 130 mil en T-bills afuera, el fondo suma {sk(d("S1","F","T"))} con Milei y AO29 {sk(d("S1","A","T"))}; repagar caución {sk(d("S1","R","T"))}. Lo que el capital compra es, sobre todo, un camino más tranquilo: menor apalancamiento antes de la elección y menos dólares que traer de urgencia si sale mal. En la reestructuración, Nada con T-bills afuera termina en {k_(fin(R,"S3","T"))} contra {k_(fin(R,"S3","F"))} del fondo, y necesita traer {k_(cob["N"])} en oct-27 (para entonces tendrías ~{k_(sum(v * (1 + a.tbill / 100) ** ((12 - m) / 12) for m, v in APO.items()))} en T-bills).</p>
<h4>2. Retorno si se paga contra pérdida si se reestructura</h4>
<p>Contra el fondo, AO29 gana {k_(d("S1","A","F"))} en Milei y {k_(d("S2","A","F"))} en oposición, y pierde {k_(-d("S3","A","F"))} en la reestructuración: arriesga ~{c1(-d("S3","A","F")/((d("S1","A","F")+d("S2","A","F"))/2))} por cada 1 que puede ganar. El umbral es <b>{bA:.0f} % de probabilidad de reestructuración</b> (con Milei y oposición con el mismo peso); si la salida del canje es peor, {bAs:.0f} %. Mitad y mitad tiene el mismo umbral con la mitad de la apuesta.</p>
<h4>3. Rendimiento contra apalancamiento</h4>
<p>Repagar baja el apalancamiento a {x2(row("S1","R",5)["lev"])} en mar-27 (contra {x2(row("S1","F",5)["lev"])} con el fondo) pero cuesta {k_(d("S1","F","R"))} a {k_(d("S3","F","R"))} de resultado. Con la caución a 2 %, la diferencia baja a {k_(d("S1","F","R",C2))}–{k_(d("S3","F","R",C2))}. Repagar empieza a convenir si la caución se acerca al {c1(P["fondo"])} % del fondo.</p>
<h4>4. Liquidez para oct-27</h4>
<p>En la reestructuración, el peor mes es oct-27. Para volver a 3x (usando primero el fondo propio): {", ".join(f"{CORTO[e]} {k_(cob[e])}" for e in ("N", "R", "F", "A", "M"))}. El fondo es el que menos necesita porque el capital ya está adentro y líquido.</p>
<h4>5. Concentración</h4>
<p>Hoy el AO29 es el {100*r0["ao29"]/r0["bruto"]:.0f} % de los activos de Cocos. Con AO29 llega al {100*row("S1","A",5)["ao29"]/row("S1","A",5)["bruto"]:.0f} %; con el fondo baja al {100*row("S1","F",5)["ao29"]/row("S1","F",5)["bruto"]:.0f} %.</p>
<h4>6. Reversibilidad y momento</h4>
<p>No hacer nada y el fondo son reversibles hasta sep-27; repagar y comprar AO29 no. La ventaja de AO29 se gana estando comprado antes de la elección: después solo queda el carry hasta el vencimiento.</p>
<h4>7. La regla de venta de largos</h4>
<p>Con Milei, la regla vende todos los largos en oct-27. Sin la regla, el resultado sería {k_(fin(SG,"S1","F")-fin(R,"S1","F"))} mejor en todas las alternativas, porque los largos siguen subiendo después de la elección. Es el costo de bajar la exposición a AR cuando el mercado lo permite.</p>'''

senales = f'''<ul>
<li><b>Ahora (nov-26):</b> decidir si se pone capital. Si la respuesta es “todavía no”, los 130 mil afuera en T-bills mantienen la opción abierta.</li>
<li><b>Riesgo país antes de mar-27.</b> Si baja de {int(P["umbral_ao29"])} pb mientras entran los aportes, la alternativa AO29 deja de comprar.</li>
<li><b>Septiembre de 2027.</b> Punto de decisión con la previa a la vista: con el fondo, mantenerlo, repagar o pasar a AO29. En la previa que sube a 1.200, el apalancamiento llega a {x2(row("S1","F",11,V["1200"])["lev"])} con el fondo y {x2(row("S1","N",11,V["1200"])["lev"])} con Nada.</li>
<li><b>Tasa de caución:</b> si se acerca al {c1(P["fondo"])} %, repagar pasa a convenir.</li>
<li><b>Escalones de la regla de venta</b> (600/500/400 pb): avisa el email del viernes.</li>
<li><b>Liquidez afuera para oct-27:</b> {k_(cob["F"])} a {k_(cob["N"])} según la alternativa, para cubrir margen si hay reestructuración.</li>
</ul>'''

lv0, lv1 = rango("lev"); n0, n1 = rango("neto"); nm0, nm1 = rango("neto_menos_aportes")
temporal = ('<div class="leg">' + "".join(f'<span class="lg"><svg width="30" height="10"><line x1="0" x2="30" y1="5" y2="5" stroke="var(--text)" stroke-width="2"{(" stroke-dasharray=" + chr(34) + dd + chr(34)) if dd else ""}/></svg>Previa: {l}</span>' for l, dd in (("baja a 800", ""), ("sube a 1.000", "7 4"), ("sube a 1.200", "2 3"))) + '</div><div class="grid3">'
            + "".join(panel(SCN[s], [(k, f"Previa {k}", "var(--text)", dd, V[k][s]["rp_path"]) for k, dd in (("800", ""), ("1000", "7 4"), ("1200", "2 3"))], "rp", 0, 2200, labels=False) for s in SC) + '</div>')
temporal = ('<h4>Riesgo país supuesto (pb)</h4><p class="desc">Desde 938 pb (BondTerminal, 6/11/2026). Tres previas hasta sep-27; en oct-27 cada escenario salta a su nivel.</p>' + temporal + leg
            + bloque("Apalancamiento de Cocos (activos / neto)", "1,0x = sin caución. Eje recortado en 5x; la línea se corta cuando el neto es negativo.", "lev", "lev", 1.0, min(round(lv1 + 0.2, 1), 5.0))
            + bloque("Caución (USD)", "Lo que queda por devolver. Baja con el capital nuevo (solo en Repagar), los cupones, los vencimientos y la venta de largos.", "caucion", "usd", 0, 500000)
            + bloque("Patrimonio neto de Cocos (activos a precio de mercado − caución, USD)", "Incluye el capital aportado. Por debajo de cero, la cuenta no cubre la caución y hay que inyectar.", "neto", "usd", math.floor(n0 / 100000) * 100000, round(n1 / 100000 + 1) * 100000)
            + bloque("Neto de Cocos menos capital aportado (USD)", "La medida para comparar: descuenta los 130 mil aportados. La distancia a Nada es lo que ganó (o perdió) ese capital.", "neto_menos_aportes", "usd", math.floor(nm0 / 100000) * 100000, round(nm1 / 100000 + 1) * 100000))

page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cocos: cómo administrar la cartera</title>
<style>
:root{{--bg:#fcfcfb;--text:#0b0b0b;--muted:#52514e;--grid:#e6e5e1;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--bar:#b9b8b2;--card:#fff;--line:#d6d5d0}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--bar:#5d5c57;--card:#222220;--line:#3d3c38}}}}
:root[data-theme=dark]{{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--bar:#5d5c57;--card:#222220;--line:#3d3c38}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 Arial,Helvetica,sans-serif;padding:16px}}main{{max-width:1100px;margin:0 auto}}
h1{{font-size:21px;margin:0 0 4px}}h2{{font-size:17px;margin:30px 0 6px;border-bottom:1px solid var(--line);padding-bottom:4px}}h4{{margin:16px 0 4px;font-size:14px}}p{{margin:4px 0 8px}}
.desc,.note{{color:var(--muted)}}.note{{font-size:12px}}ul.key li{{margin-bottom:6px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}}.card h4{{margin-top:0}}
.panel{{margin:8px 0;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px;position:relative}}figcaption{{font-weight:bold;font-size:12px;margin-bottom:4px}}
.grid3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}.sub{{font-size:12px;font-weight:bold;margin-bottom:2px}}
svg{{width:100%;height:auto;display:block}}.ax{{fill:var(--muted);font-size:10px}}.val{{fill:var(--text);font-size:11px;font-variant-numeric:tabular-nums}}.axis{{stroke:var(--muted);stroke-width:1}}
.grid{{stroke:var(--grid);stroke-width:1}}.lab{{font-size:11px;font-weight:bold;fill:var(--text)}}.ev{{stroke:var(--muted);stroke-dasharray:2 3;stroke-width:1}}.cross{{stroke:var(--muted);stroke-width:1}}
.tip{{position:absolute;top:30px;left:50px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;pointer-events:none;white-space:nowrap;z-index:2}}
.leg{{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0}}.lg{{display:inline-flex;align-items:center;gap:6px;font-size:12px;white-space:nowrap}}
table{{border-collapse:collapse;font-size:12px;margin:8px 0;display:block;overflow-x:auto}}th,td{{border:1px solid var(--line);padding:4px 7px;text-align:center;vertical-align:top}}th{{background:var(--grid)}}td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}td.l{{text-align:left}}
.tag{{font-size:10px;border:1px solid var(--line);border-radius:4px;padding:0 4px;color:var(--muted)}}details{{margin:10px 0}}summary{{cursor:pointer;font-weight:bold}}
</style></head><body><main>
<h1>Cocos · cómo administrar la cartera hasta oct-2029</h1>
<p class="desc">Escenarios, alternativas y trade-offs. Proyección mensual nov-26 a oct-29 (vence el AO29). Gráficos y tablas con la previa que sube a 1.000 pb, salvo que se indique otra. Sin margin call: si el neto de Cocos queda negativo, cubrís el margen con dólares de afuera y el informe dice cuánto.</p>
{proposito}

<h2>En pocas palabras</h2>{resumen}
{barras(ALL, "Resultado en oct-29: neto de Cocos menos capital aportado (USD)")}

<h2>1. Punto de partida</h2>
<table><tr><th>Bonos AR</th><th>de los cuales AO29</th><th>Largos (AL35, AE38, AL41, GD46, GD29)</th><th>Notas</th><th>Efectivo</th><th>Activos</th><th>Caución</th><th>Neto</th><th>Apalancamiento</th><th>TIR promedio</th><th>Duration</th></tr>
<tr><td class="n">{k_(r0["ar"])}</td><td class="n">{k_(r0["ao29"])}</td><td class="n">{k_(r0["largos"])}</td><td class="n">{k_(r0["notas"])}</td><td class="n">{k_(r0["fondo"])}</td><td class="n">{k_(r0["bruto"])}</td><td class="n">{k_(r0["caucion"])}</td><td class="n">{k_(r0["neto"])}</td><td class="n"><b>{x2(r0["lev"])}</b></td><td class="n">{c1(TIR)} %</td><td class="n">{c1(DUR)}</td></tr></table>
<p class="note">Posiciones del estado de Cocos del 31/10 a precios de BondTerminal del 6/11/2026 (MEP), riesgo país 938 pb. Caución USD {c1(P["caucion_tasa"])} % anual (variable).</p>

<h2>2. Los escenarios</h2>
<div class="cards">{esc_txt}</div>
<h4>Precios supuestos</h4>{t_precios()}

<h2>3. Las alternativas</h2>
<p>Si se pone capital, el calendario es 15 mil en nov-26 y dic-26, 70 mil en ene-27, 15 mil en feb-27 y mar-27; entra desde afuera y se canjea cable a MEP (+{c1(P["gap"])} %). En todas las alternativas, los flujos de la cuenta (cupones, vencimientos de notas, venta escalonada de largos) repagan caución.</p>
{alt_txt}

<h2>4. Resultados</h2>
<h4>Neto de Cocos en oct-29 menos capital aportado</h4>{t_matriz(ALL)}
<h4>El camino hasta la elección</h4>{t_camino(tuple(e for e in ALL if e != "T"))}
<h4>Reestructuración: el escenario que separa a las alternativas</h4>{t_s3(ALL)}

<h2>5. Proyección en el tiempo</h2>
<p class="desc">Las cuatro alternativas principales en cada escenario. Pasá el cursor por un gráfico para ver los valores de cada mes.</p>
{temporal}
<h4>Valuación de la cartera por hito (USD)</h4>{t_valuacion()}
<h4>Flujos acumulados nov-26 a oct-29 (USD)</h4><p class="desc">Lo que entró y salió de la cuenta, aparte del capital nuevo.</p>{t_flujos()}

<h2>6. Trade-offs</h2>{trade}

<h2>7. Sensibilidades</h2>{t_sens(ALL)}
<h4>Según la previa</h4>{t_previa(ALL)}
<p class="note">La previa cambia el camino pero casi no el resultado final, porque en la elección los bonos se revalúan al nivel de cada escenario.</p>

<h2>8. Qué mirar y cuándo decidir</h2>{senales}

<h2>Supuestos y límites</h2>
<p class="note">AO29: cupón 6 % pagado 0,5 % por mes, vence oct-29; comprado a {c1(a.compra_ao29)} (dato de Ivo). Largos: bonos sintéticos calibrados a precio y duration de BondTerminal, cupón semestral. TIR = UST + spread proporcional al riesgo país. Reestructuración: desde la elección, cada bono vale el {100-int(P["quita"])} % del precio del bono nuevo (cupón {c1(P["cupon_nuevo"])} %, 2035) a TIR UST + riesgo país. Notas (70 mil) con cupones y capital al par, sin barreras. “Nada + T-bills afuera”: los aportes del calendario quedan en T-bills al {c1(a.tbill)} %, sin canje. Sin margin call; las inyecciones de cobertura se informan, no se simulan. Umbrales de probabilidad con Milei y oposición con el mismo peso. Modelo de escenarios, no predicción; no es asesoramiento financiero.</p>
</main>
<script>
document.querySelectorAll('figure.tl').forEach(function(f){{
  var d=JSON.parse(f.querySelector('script').textContent),svg=f.querySelector('svg'),hit=f.querySelector('.hit'),cr=f.querySelector('.cross'),tip=f.querySelector('.tip');
  var M={json.dumps(MESN)},n=d.s[0].v.length;
  function f2(v){{if(v===null)return 'neto < 0';if(d.m==='rp')return Math.round(v)+' pb';if(d.m==='lev')return v.toFixed(2).replace('.',',')+'x';return 'USD '+Math.round(v/1000).toLocaleString('es-AR')+' mil';}}
  hit.addEventListener('mousemove',function(e){{var r=svg.getBoundingClientRect(),sc=r.width/svg.viewBox.baseVal.width,x=(e.clientX-r.left)/sc;var i=Math.max(0,Math.min(n-1,Math.round((x-d.ml)/d.iw*(n-1))));var px=d.ml+d.iw*i/(n-1);cr.setAttribute('x1',px);cr.setAttribute('x2',px);cr.style.display='';
    tip.innerHTML='<b>'+M[i]+(i===0?' (hoy)':'')+'</b><br>'+d.s.map(function(s){{return '<span style="color:'+s.c+'">●</span> '+s.l+': '+f2(s.v[i]);}}).join('<br>');tip.style.display='';tip.style.left=Math.min(r.width-200,Math.max(4,px*sc+8))+'px';}});
  hit.addEventListener('mouseleave',function(){{cr.style.display='none';tip.style.display='none';}});
}});
</script></body></html>'''
open(a.out, "w").write(page)
print("ok", len(page))
