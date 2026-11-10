#!/usr/bin/env python3
"""Informe de decisión para la cuenta de Cocos: cómo administrar una cartera de bonos AR comprada a paridades más altas, con caución.
Plantea la decisión en dos niveles: (1) poner o no capital nuevo (hasta 130 mil entre nov-26 y mar-27) y (2) si se pone, dónde.
Lee las salidas JSON de proyeccion_cocos.py (base y sensibilidades): narrativa, tablas, gráfico de resultados y proyecciones temporales.
Uso: informe_decision_cocos.py --dir <carpeta con pc_800/1000/1200.json, pc_1000_sinrec.json, pc_1000_cau2.json, pc_500.json> --out informe.html
Sin margin call: si el neto de Cocos queda negativo, Ivo inyecta USD para cubrir el margen (se informa cuánto)."""
import json, argparse, os, sys, html, math, importlib.util

ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--tbill", type=float, default=4.1, help="tasa de T-bills para el capital que queda afuera en 'Nada'")
ap.add_argument("--compra-ao29", type=float, default=95.0, help="precio de compra del AO29 (Ivo)")
a = ap.parse_args()
L = lambda f: json.load(open(os.path.join(a.dir, f)))
B = L("pc_1000.json"); R = B["resultados"]; P = B["parametros"]; APO = {int(k): v for k, v in B["aportes"].items()}
V = {k: L(f"pc_{k}.json")["resultados"] for k in ("800", "1000", "1200")}
SR, C2, SG = L("pc_1000_sinrec.json")["resultados"], L("pc_1000_cau2.json")["resultados"], L("pc_500.json")["resultados"]
argv, sys.argv = sys.argv, [sys.argv[0]]
sp = importlib.util.spec_from_file_location("pc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "proyeccion_cocos.py"))
pc = importlib.util.module_from_spec(sp); sp.loader.exec_module(pc); sys.argv = argv
ESC = pc.escenarios()

SC = ("S1", "S2", "S3"); BASE4 = ("N", "R", "A"); ALL = BASE4
NOM = dict(B["estrategias"]); NOM["T"] = "Nada, con los 130 mil en T-bills afuera"
CORTO = {"N": "Nada", "T": "Nada + T-bills afuera", "R": "Repagar caución", "F": "Fondo USD", "A": "AO29 si RP>700", "M": "Mitad fondo / AO29", "P": "Fondo → repago sep-27"}
SCN = {"S1": "Milei reelecto", "S2": "Oposición con shock", "S3": "Reestructuración (canje)"}
STY = {"N": ("var(--muted)", "6 4"), "R": ("var(--s1)", ""), "A": ("var(--s2)", "")}
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
def be(e, f="R", RR=R):
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
SHORT = {"N": "Nada", "R": "Repagar", "A": "AO29"}
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
    return h + '</div><p class="note">En azul, la mejor de cada escenario. Neto de Cocos en oct-29 menos el capital aportado; con Nada, los 130 mil quedan afuera y no se cuentan.</p></figure>'

# ---------- tablas ----------
def t_precios():
    hit = [(0, "hoy"), (5, "mar-27"), (11, "sep-27"), (12, "oct-27"), (20, "jun-28"), (36, "oct-29")]
    t = '<table><tr><th>Escenario</th><th>Bono</th>' + "".join(f"<th>{l}</th>" for _, l in hit) + '</tr>'
    for s in SC:
        for i, b in enumerate(("AO29", "AL35")):
            t += f'<tr>{f"<td rowspan=2 class=l>{SCN[s]}</td>" if i == 0 else ""}<td>{b}</td>' + "".join(f'<td class="n">{c1(pc.px(b, m, ESC[s]))}</td>' for m, _ in hit) + '</tr>'
    return t + '</table><p class="note">Precio por 100 de nominal. En la reestructuración, desde la elección el precio es el del paquete del canje (75 % del bono nuevo); en jun-28 se canjea.</p>'

def t_matriz(ests):
    t = '<table><tr><th>Decisión</th>' + "".join(f'<th>{SCN[s]}</th>' for s in SC) + '<th>Promedio simple</th><th>Peor caso</th><th>Distancia mejor-peor</th></tr>'
    for e in ests:
        v = [fin(R, s, e) for s in SC]
        t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{k_(x)}</td>' for x in v) + f'<td class="n">{k_(sum(v)/3)}</td><td class="n">{k_(min(v))}</td><td class="n">{k_(max(v)-min(v))}</td></tr>'
    return t + '</table>'

def t_camino(ests):
    cols = [("Apal. mar-27", lambda e: x2(row("S1", e, 5)["lev"])), ("Capacidad de compra a 2x, mar-27", lambda e: k_(row("S1", e, 5)["capacidad_2x"])),
            ("Caución sep-27", lambda e: k_(row("S1", e, 11)["caucion"])), ("Apal. sep-27", lambda e: x2(row("S1", e, 11)["lev"])),
            ("AO29 / activos de Cocos, mar-27", lambda e: f'{100*row("S1", e, 5)["ao29"]/row("S1", e, 5)["bruto"]:.0f} %')]
    t = '<table><tr><th>Decisión</th>' + "".join(f"<th>{c}</th>" for c, _ in cols) + '</tr>'
    for e in ests: t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{fn(e)}</td>' for _, fn in cols) + '</tr>'
    return t + '</table><p class="note">Antes de la elección los tres escenarios son iguales.</p>'

def t_s3(ests):
    t = '<table><tr><th>Decisión</th><th>Neto oct-27 (peor mes)</th><th>Apal. oct-27</th><th>Inyección para neto ≥ 0</th><th>Inyección para volver a 3x</th><th>Neto oct-29</th><th>Caución oct-29</th><th>Si el riesgo país no baja de 2.000: neto − aportes</th></tr>'
    for e in ests:
        f_, n0, n3 = cobertura("S3", e)
        t += (f'<tr><td class="l">{NOM[e]}</td><td class="n">{k_(nmin("S3", e))}</td><td class="n">{x2(row("S3", e, 12)["lev"])}</td><td class="n">{k_(n0) if n0 else "–"}</td>'
              f'<td class="n"><b>{k_(n3)}</b></td><td class="n">{k_(row("S3", e, 36)["neto"])}</td><td class="n">{k_(row("S3", e, 36)["caucion"])}</td><td class="n">{k_(fin(SR, "S3", e))}</td></tr>')
    return t + '</table><p class="note">La inyección no cambia el resultado económico: es capital que entra y repaga caución. Lo que cambia es cuánto tenés que tener disponible en oct-27. 3x es una referencia; tu acuerdo de margen con Cocos puede ser otro. Con Nada, los 130 mil que quedaron afuera (más intereses) están disponibles para esa cobertura.</p>'

def t_valuacion():
    hit = [(5, "mar-27"), (11, "sep-27"), (12, "oct-27"), (14, "dic-27"), (24, "oct-28"), (36, "oct-29")]
    t = '<table><tr><th>Escenario</th><th>Decisión</th>' + "".join(f'<th colspan="4">{l}</th>' for _, l in hit) + '</tr><tr><th></th><th></th>' + '<th>Bonos AR</th><th>Fondo</th><th>Caución</th><th>Neto</th>' * len(hit) + '</tr>'
    for s in SC:
        for i, e in enumerate(BASE4):
            rr = R[s]["estrategias"][e]
            t += f'<tr>{f"<td rowspan=4 class=l>{SCN[s]}</td>" if i == 0 else ""}<td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{k_(rr[m]["ar"])}</td><td class="n">{k_(rr[m]["fondo"])}</td><td class="n">{k_(rr[m]["caucion"])}</td><td class="n"><b>{k_(rr[m]["neto"])}</b></td>' for m, _ in hit) + '</tr>'
    return t + '</table>'

def t_flujos():
    cols = [("cupones", "Cupones cobrados"), ("venc_notas", "Vencimiento de notas"), ("venta_largos", "Venta de largos"), ("venc_ao29", "Vencimiento AO29"),
            ("interes_caucion", "Intereses de caución"), ("compra_ao29", "Compras de AO29"), ("rend_fondo", "Rendimiento del fondo")]
    t = '<table><tr><th>Escenario</th><th>Decisión</th>' + "".join(f'<th>{l}</th>' for _, l in cols) + '<th>Caución oct-29</th></tr>'
    for s in SC:
        for i, e in enumerate(BASE4):
            f = R[s]["estrategias"][e][36]
            t += f'<tr>{f"<td rowspan=4 class=l>{SCN[s]}</td>" if i == 0 else ""}<td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{k_(f[k]) if f[k] else "–"}</td>' for k, _ in cols) + f'<td class="n">{k_(f["caucion"])}</td></tr>'
    return t + '</table>'

def t_sens(ests):
    rows_ = [("Base (caución 0,5 % + 1 pp, previa 1.000)", R), ("Caución a 2 % + 1 pp", C2), ("Previa optimista: baja a 500 pb en jun-27 (activa la regla de venta)", SG), ("Reestructuración sin recuperación (RP 2.000)", SR)]
    t = '<table><tr><th>Sensibilidad</th><th>Escenario</th>' + "".join(f'<th>{CORTO[e]}</th>' for e in ests) + '</tr>'
    for nombre, RR in rows_:
        for i, s in enumerate(SC):
            best = max(ests, key=lambda e: fin(RR, s, e))
            t += f'<tr>{f"<td rowspan=3 class=l>{nombre}</td>" if i == 0 else ""}<td class="l">{SCN[s]}</td>' + "".join(f'<td class="n">{"<b>" if e == best else ""}{k_(fin(RR, s, e))}{"</b>" if e == best else ""}</td>' for e in ests) + '</tr>'
    return t + '</table><p class="note">Neto oct-29 menos capital aportado. En negrita, la mejor de cada fila.</p>'

def t_previa(ests):
    t = '<table><tr><th>Decisión</th>' + "".join(f'<th>Apal. sep-27, previa {k}</th>' for k in V) + "".join(f'<th>Neto − aportes en reestructuración, previa {k}</th>' for k in V) + '</tr>'
    for e in ests:
        t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{x2(row("S1", e, 11, V[k])["lev"])}</td>' for k in V) + "".join(f'<td class="n">{k_(fin(V[k], "S3", e))}</td>' for k in V) + '</tr>'
    return t + '</table>'

# ---------- texto ----------
bA, bAs, bA2 = be("A"), be("A", RR=SR), be("A", RR=C2)
cob = {e: cobertura("S3", e)[2] for e in ALL}
salto = pc.px("AO29", 12, ESC["S1"]) - pc.px("AO29", 11, ESC["S1"])
r0 = row("S1", "N", 0)
CT = P["caucion_tasa"] + P["comision_caucion"]          # costo total de la caución
pct = lambda e, m=5: f'{100*row("S1", e, m)["ao29"]/row("S1", e, m)["bruto"]:.0f} %'
up = lambda e, f: (d("S1", e, f) + d("S2", e, f)) / 2

proposito = f'''<p>La cartera de Cocos quedó invertida en bonos argentinos comprados a paridades más altas que las actuales (por ejemplo, el AO29 se compró a {c1(a.compra_ao29)} y hoy cotiza a {c1(P_AO)}: unos {k_(PERD_AO)} de pérdida no realizada solo en ese bono) y está financiada con caución. El devengamiento juega a favor: la cartera rinde una TIR promedio de {c1(TIR)} % (unos {k_(DEV)} por año sobre el valor de mercado) contra un costo de caución de {c1(CT)} % ({k_(pc.CAUCION0 * CT / 100)} por año). Pero la sensibilidad al riesgo político es alta: con una duration de {c1(DUR)}, cada 100 pb de suba del riesgo país le saca unos {k_(DV100)} al valor de la cartera, y la elección de octubre de 2027 abre futuros muy distintos.</p>
<p>El objetivo es ayudarte a decidir cómo administrar esa cartera hasta oct-29, cuando vence el AO29. Hay tres decisiones posibles:</p>
<ol><li><b>Nada</b>: no aportar capital y dejar que el devengamiento y los cupones vayan bajando la caución.</li>
<li><b>Repagar caución</b>: aportar hasta 130 mil entre nov-26 y mar-27 y usarlos para devolver caución.</li>
<li><b>AO29 si el riesgo país está arriba de {int(P["umbral_ao29"])} pb</b>: aportar lo mismo y comprar más AO29.</li></ol>
<p>Para responder, el informe sigue este orden:</p>
<ol><li><b>Punto de partida y premisas</b>: la cartera de hoy y las reglas que valen en todos los casos.</li>
<li><b>Escenarios</b>: qué puede pasar con el riesgo país antes y después de la elección, y cómo se valúan los bonos en cada caso.</li>
<li><b>Las tres decisiones</b>: qué hace cada una.</li>
<li><b>Resultados y proyección en el tiempo</b>: cada decisión en cada escenario, mes a mes hasta oct-29.</li>
<li><b>Pros y contras, trade-offs y sensibilidades</b>.</li>
<li><b>Conclusiones y qué mirar</b>.</li></ol>'''

resumen = f'''<ul class="key">
<li><b>Nada es viable si se paga la deuda, pero deja la cartera expuesta.</b> Con Milei o con la oposición termina {k_(-up("N","R"))} debajo de repagar y {k_(-up("N","A"))} debajo de AO29 (sin contar lo que los 130 mil rindan afuera: ~{k_(TB)} en T-bills). El costo es el camino: {x2(row("S1","N",11)["lev"])} de apalancamiento en la previa y, si hay reestructuración, neto de Cocos de {k_(nmin("S3","N"))}: necesitás {k_(cob["N"])} para volver a 3x.</li>
<li><b>Repagar caución le gana a Nada en los tres escenarios</b> ({sk(d("S1","R","N"))}, {sk(d("S2","R","N"))}, {sk(d("S3","R","N"))}), porque cada dólar repagado ahorra {c1(CT)} % de caución y captura el {c1(P["gap"])} % del canje. Es la que mejor protege: neto mínimo de {k_(nmin("S3","R"))} y {k_(cob["R"])} de cobertura en la reestructuración.</li>
<li><b>AO29 contra repagar es una apuesta a la elección de oct-27.</b> AO29 deja {sk(up("A","R"))} si se paga y {sk(d("S3","A","R"))} si hay reestructuración. Conviene solo si la probabilidad de reestructuración es menor a <b>{bA:.0f} %</b> ({bAs:.0f} % si después del canje el riesgo país no baja). Además sube la concentración en AO29 a {pct("A")} de los activos de Cocos y necesita {k_(cob["A"])} de cobertura en la reestructuración.</li>
<li><b>Lo que se decide ahora y lo que puede esperar.</b> Repagar y comprar AO29 se hacen entre nov-26 y mar-27, y no se deshacen sin costo. La suba de la elección (AO29 +{c1(salto)} puntos si gana Milei) solo la captura quien está comprado antes.</li>
</ul>'''

esc_txt = f'''
<div class="card"><h4>Milei reelecto</h4><p>El riesgo país pasa de ~1.000 a <b>{int(P["s1"])} pb</b> en oct-27. El AO29 sube de {c1(pc.px("AO29",11,ESC["S1"]))} a {c1(pc.px("AO29",12,ESC["S1"]))} y los largos de ~64 a ~90. Los largos no se venden (la regla de venta rige solo antes de la elección) y siguen subiendo hasta ~{c1(pc.px("AL35",36,ESC["S1"]))} en oct-29. El AO29 vence en oct-29 y la caución termina en cero.</p>
<p><b>Qué pesa:</b> cuánto AO29 tenés el día de la elección, porque en ese mes sube {c1(salto)} puntos. Después solo queda el carry hasta el vencimiento.</p></div>
<div class="card"><h4>Oposición con shock</h4><p>El riesgo país salta a <b>{int(P["s2_peak"])} pb</b> por {P["s2_hold"]} meses y baja a {int(P["s2_end"])} en oct-29; la deuda se paga. El AO29 cae a {c1(pc.px("AO29",12,ESC["S2"]))}, pero al ser corto vuelve a 100 al vencer. Los largos caen a ~51 y terminan en ~{c1(pc.px("AL35",36,ESC["S2"]))}. No se activa la regla de venta.</p>
<p><b>Qué pesa:</b> el AO29 se recupera porque vence a la par en oct-29; el shock se siente en el camino. La cartera de hoy, sin aportes, pasaría de {x2(row("S2","N",11)["lev"])} de apalancamiento en sep-27 a {x2(row("S2","N",12)["lev"])} en oct-27.</p></div>
<div class="card"><h4>Reestructuración (canje)</h4><p>Riesgo país a 2.000 pb en oct-27, default en dic-27, canje en jun-28 por un bono nuevo con quita del {int(P["quita"])} % del nominal, cupón {c1(P["cupon_nuevo"])} % y vencimiento 2035. Desde la elección cada bono vale unos {c1(pc.px("AO29",12,ESC["S3"]))} centavos y sube a {c1(pc.px("AO29",36,ESC["S3"]))} en oct-29 a medida que el riesgo país baja a {int(P["s3_end"])} pb y vuelven los cupones.</p>
<p><b>Qué pesa:</b> cuánto expuesto a bonos AR estás el día de la elección. La cartera de hoy pierde ~{k_(row("S3","N",11)["ar"]-row("S3","N",12)["ar"])} en un mes y, sin capital adicional, el neto de Cocos queda en {k_(row("S3","N",12)["neto"])}: hay que cubrir el margen.</p></div>'''

alt_def = f'''<table><tr><th>Decisión</th><th>Qué hace</th><th>Qué busca</th></tr>
<tr><td class="l">Nada</td><td>No se aporta. La cartera sigue igual; cupones y vencimientos van bajando la caución.</td><td>No sumar dólares a Argentina y dejar que el devengamiento haga el trabajo. Los 130 mil quedan afuera.</td></tr>
<tr><td class="l">Repagar caución</td><td>El capital se canjea cable a MEP y devuelve caución.</td><td>Bajar el apalancamiento lo más rápido posible, ahorrar el {c1(CT)} % de la caución y recuperar capacidad de compra.</td></tr>
<tr><td class="l">AO29 si RP&gt;{int(P["umbral_ao29"])}</td><td>El capital se canjea y compra AO29 a precio de mercado mientras el riesgo país esté arriba de {int(P["umbral_ao29"])} pb; si está por debajo, no compra y queda en el fondo USD de Cocos.</td><td>Aprovechar la TIR alta (~{c1(pc.BONOS["AO29"][2])} %) y la suba si el riesgo país baja.</td></tr>
</table>'''

alt_txt = f'''<table><tr><th>Decisión</th><th>A favor</th><th>En contra</th></tr>
<tr><td class="l">Nada</td><td>No compromete dólares nuevos en Argentina; los 130 mil quedan afuera, rindiendo (~{k_(TB)} en T-bills a oct-29) y disponibles para cubrir margen. Es reversible: se puede aportar más adelante.</td><td>Es la que menos rinde en Cocos en los tres escenarios. Apalancamiento alto todo el camino ({x2(row("S1","N",11)["lev"])} en sep-27). En la reestructuración, neto de Cocos de {k_(nmin("S3","N"))} y {k_(cob["N"])} para volver a 3x.</td></tr>
<tr><td class="l">Repagar caución</td><td>Le gana a Nada en los tres escenarios. El menor apalancamiento ({x2(row("S1","R",5)["lev"])} en mar-27) y la mayor capacidad de compra a 2x ({k_(row("S1","R",5)["capacidad_2x"])}). La que mejor resiste la reestructuración ({k_(cob["R"])} de cobertura).</td><td>Deja pasar la suba de la elección si se paga la deuda ({sk(-up("A","R"))} contra AO29). La plata queda trabada como menor deuda.</td></tr>
<tr><td class="l">AO29 si RP&gt;{int(P["umbral_ao29"])}</td><td>La mejor si se paga la deuda ({sk(d("S1","A","R"))} contra repagar con Milei, {sk(d("S2","A","R"))} con la oposición). Su cupón mensual también repaga caución.</td><td>La peor en la reestructuración ({sk(d("S3","A","R"))} contra repagar). AO29 llega al {pct("A")} de los activos de Cocos y necesita {k_(cob["A"])} de cobertura en oct-27.</td></tr>
</table>'''

trade = f'''
<h4>1. Aportar o no</h4>
<p>Aportar mejora el resultado en Cocos en casi todos los casos, pero esa plata también rendiría afuera. Contra Nada, repagar suma {k_(d("S1","R","N"))} a {k_(d("S3","R","N"))}; los mismos 130 mil en T-bills afuera ganarían ~{k_(TB)}. Repagar le gana a Nada por el canje ({c1(P["gap"])} %) y por el costo de la caución ({c1(CT)} %), pero no por mucho. Lo que compra, sobre todo, es un camino más tranquilo: menos apalancamiento antes de la elección y menos dólares que traer de urgencia si sale mal ({k_(cob["R"])} contra {k_(cob["N"])}).</p>
<h4>2. Retorno si se paga contra pérdida si se reestructura</h4>
<p>Contra repagar, AO29 gana {k_(d("S1","A","R"))} con Milei y {k_(d("S2","A","R"))} con la oposición, y pierde {k_(-d("S3","A","R"))} en la reestructuración: arriesga ~{c1(-d("S3","A","R")/up("A","R"))} por cada 1 que puede ganar. El umbral es <b>{bA:.0f} % de probabilidad de reestructuración</b> (con Milei y oposición con el mismo peso): si creés que es menor, AO29 tiene mejor valor esperado; si es mayor, repagar. Si después del canje el riesgo país no baja de 2.000, el umbral cae a {bAs:.0f} %.</p>
<h4>3. Liquidez para oct-27</h4>
<p>En la reestructuración, el peor mes es oct-27. Para volver a 3x: Nada {k_(cob["N"])}, repagar {k_(cob["R"])}, AO29 {k_(cob["A"])}. Con Nada, los 130 mil que quedaron afuera cubren parte (para entonces serían ~{k_(sum(v * (1 + a.tbill / 100) ** ((12 - m) / 12) for m, v in APO.items()))}).</p>
<h4>4. Concentración</h4>
<p>Hoy el AO29 es el {100*r0["ao29"]/r0["bruto"]:.0f} % de los activos de Cocos. Con Nada y con repagar sigue igual; con AO29 llega al {pct("A")}.</p>
<h4>5. Costo de la caución</h4>
<p>Con la tasa de mercado en 0,5 % más 1 pp de comisión de Cocos, la caución cuesta {c1(CT)} %. Si la tasa de mercado sube a 2 % ({c1(2 + P["comision_caucion"])} % con comisión), repagar le gana a Nada por {k_(d("S1","R","N",C2))} a {k_(d("S3","R","N",C2))} y el umbral de AO29 contra repagar queda en {bA2:.0f} %.</p>
<h4>6. Reversibilidad y momento</h4>
<p>Nada es la única reversible: se puede aportar más adelante. Repagar y comprar AO29 no se deshacen sin costo. La ventaja de AO29 se gana estando comprado antes de la elección; después solo queda el carry hasta el vencimiento.</p>
<h4>7. La regla de venta de largos</h4>
<p>La regla rige solo antes de la elección: después, con el escenario despejado, no tiene sentido vender, porque los bonos se pagan o se canjean. En las tres previas modeladas el riesgo país no baja de 800 antes de oct-27, así que la regla no se activa. Si la previa fuera mucho mejor (riesgo país a 500 pb en jun-27), se venderían la mitad de los largos por unos {k_(row("S1","N",36,SG)["venta_largos"])} antes de la elección: el resultado baja {k_(fin(R,"S1","R")-fin(SG,"S1","R"))} con Milei (se vende antes de la suba) y sube {k_(fin(SG,"S3","R")-fin(R,"S3","R"))} en la reestructuración (se sale antes de la caída). Es un seguro que se paga en los escenarios buenos.</p>'''

senales = f'''<ul>
<li><b>Ahora (nov-26):</b> decidir si se aporta. Si la respuesta es “todavía no”, Nada mantiene la opción abierta.</li>
<li><b>Riesgo país antes de mar-27.</b> Si baja de {int(P["umbral_ao29"])} pb mientras entran los aportes, la decisión AO29 deja de comprar.</li>
<li><b>Septiembre de 2027.</b> La previa a la vista: en el camino que sube a 1.200, el apalancamiento llega a {x2(row("S1","N",11,V["1200"])["lev"])} con Nada, {x2(row("S1","R",11,V["1200"])["lev"])} repagando y {x2(row("S1","A",11,V["1200"])["lev"])} con AO29.</li>
<li><b>Tasa de caución:</b> el costo real es la tasa de mercado más 1 pp; cuanto más sube, más conviene repagar.</li>
<li><b>Escalones de la regla de venta</b> (600/500/400 pb), hasta sep-27: avisa el email del viernes.</li>
<li><b>Liquidez afuera para oct-27:</b> {k_(cob["R"])} a {k_(cob["N"])} según la decisión, para cubrir margen si hay reestructuración.</li>
</ul>'''

lv0, lv1 = rango("lev"); n0, n1 = rango("neto"); nm0, nm1 = rango("neto_menos_aportes")
temporal = ('<div class="leg">' + "".join(f'<span class="lg"><svg width="30" height="10"><line x1="0" x2="30" y1="5" y2="5" stroke="var(--text)" stroke-width="2"{(" stroke-dasharray=" + chr(34) + dd + chr(34)) if dd else ""}/></svg>Previa: {l}</span>' for l, dd in (("baja a 800", ""), ("sube a 1.000", "7 4"), ("sube a 1.200", "2 3"))) + '</div><div class="grid3">'
            + "".join(panel(SCN[s], [(k, f"Previa {k}", "var(--text)", dd, V[k][s]["rp_path"]) for k, dd in (("800", ""), ("1000", "7 4"), ("1200", "2 3"))], "rp", 0, 2200, labels=False) for s in SC) + '</div>')
rp_chart = temporal
temporal = (leg
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
<p class="desc">Escenarios, decisiones y trade-offs. Proyección mensual de nov-26 a oct-29, cuando vence el AO29.</p>
<h2>1. Para qué es este análisis</h2>
{proposito}

<h2>2. Punto de partida y premisas</h2>
<table><tr><th>Bonos AR</th><th>de los cuales AO29</th><th>Largos (AL35, AE38, AL41, GD46, GD29)</th><th>Notas</th><th>Efectivo</th><th>Activos</th><th>Caución</th><th>Neto</th><th>Apalancamiento</th><th>TIR promedio</th><th>Duration</th></tr>
<tr><td class="n">{k_(r0["ar"])}</td><td class="n">{k_(r0["ao29"])}</td><td class="n">{k_(r0["largos"])}</td><td class="n">{k_(r0["notas"])}</td><td class="n">{k_(r0["fondo"])}</td><td class="n">{k_(r0["bruto"])}</td><td class="n">{k_(r0["caucion"])}</td><td class="n">{k_(r0["neto"])}</td><td class="n"><b>{x2(r0["lev"])}</b></td><td class="n">{c1(TIR)} %</td><td class="n">{c1(DUR)}</td></tr></table>
<p class="note">Posiciones del estado de Cocos del 31/10 a precios de BondTerminal del 6/11/2026 (MEP), riesgo país 938 pb.</p>
<p><b>Premisas que valen en todos los casos:</b></p>
<ul>
<li>Caución USD: tasa de mercado {c1(P["caucion_tasa"])} % + {c1(P["comision_caucion"])} pp de comisión de Cocos = <b>{c1(P["caucion_tasa"] + P["comision_caucion"])} % anual</b> (variable; en sensibilidades, 2 % + 1 pp).</li>
<li>Todo flujo de la cuenta (cupones, vencimientos de las notas, ventas de bonos) repaga caución; cuando la caución llega a cero, el excedente va al fondo USD.</li>
<li>Regla de venta escalonada de los bonos largos (AL35, AE38, AL41, GD46, GD29), decidida por vos: con riesgo país en 600 pb se vende el 25 %, en 500 pb el 50 % y en 400 pb el 100 %; lo producido repaga caución. <b>Rige solo antes de la elección</b>: después, con el escenario despejado, no se vende, porque los bonos se pagan o se canjean.</li>
<li>El capital que entra desde afuera se canjea cable a MEP con una captura del {c1(P["gap"])} %, sin comisión.</li>
<li>Sin margin call: si el neto de Cocos queda negativo, cubrís el margen con dólares de afuera. El informe muestra cuánto haría falta.</li>
<li>La medida para comparar decisiones es el <b>neto de Cocos en oct-29 menos el capital aportado</b>, para no premiar a las que ponen más plata.</li>
</ul>

<h2>3. Los escenarios</h2>
<p>Cada escenario combina dos cosas: <b>el camino del riesgo país antes de la elección</b> (la “previa”, de nov-26 a sep-27) y <b>el resultado de la elección</b> de oct-27, que fija el riesgo país de ahí en adelante.</p>
<p><b>Previas</b> (comunes a los tres resultados): baja a 800 pb en mar-27; sube a 1.000 pb en sep-27; sube a 1.200 pb en sep-27. Salvo que se indique otra cosa, el informe usa la previa que <b>sube a 1.000</b>, la más cercana al nivel actual.</p>
<p><b>Resultados de la elección:</b></p>
<div class="cards">{esc_txt}</div>
<h4>Riesgo país supuesto (pb)</h4>{rp_chart}
<h4>Precios supuestos</h4>{t_precios()}

<h2>4. Las tres decisiones</h2>
<p>Si se aporta capital, el calendario es 15 mil en nov-26 y dic-26, 70 mil en ene-27, 15 mil en feb-27 y mar-27 (130 mil en total), igual en Repagar y en AO29.</p>
{alt_def}

<h2>5. Resultados</h2>
{barras(ALL, "Resultado en oct-29: neto de Cocos menos capital aportado (USD)")}
<h4>Neto de Cocos en oct-29 menos capital aportado</h4>{t_matriz(ALL)}
<h4>El camino hasta la elección</h4>{t_camino(tuple(e for e in ALL if e != "T"))}
<h4>Reestructuración: el escenario que separa a las decisiones</h4>{t_s3(ALL)}

<h2>6. Proyección en el tiempo</h2>
<p class="desc">Las tres decisiones en cada escenario. Pasá el cursor por un gráfico para ver los valores de cada mes.</p>
{temporal}
<h4>Valuación de la cartera por hito (USD)</h4>{t_valuacion()}
<h4>Flujos acumulados nov-26 a oct-29 (USD)</h4><p class="desc">Lo que entró y salió de la cuenta, aparte del capital nuevo.</p>{t_flujos()}

<h2>7. Pros y contras de cada decisión</h2>{alt_txt}

<h2>8. Trade-offs</h2>{trade}

<h2>9. Sensibilidades</h2>{t_sens(ALL)}
<h4>Según la previa</h4>{t_previa(ALL)}
<p class="note">La previa cambia el camino pero casi no el resultado final, porque en la elección los bonos se revalúan al nivel de cada escenario.</p>

<h2>10. Conclusiones</h2>{resumen}

<h2>11. Qué mirar y cuándo decidir</h2>{senales}

<h2>Supuestos y límites</h2>
<p class="note">AO29: cupón 6 % pagado 0,5 % por mes, vence oct-29; comprado a {c1(a.compra_ao29)} (dato de Ivo). Largos: bonos sintéticos calibrados a precio y duration de BondTerminal, cupón semestral. TIR = UST + spread proporcional al riesgo país. Reestructuración: desde la elección, cada bono vale el {100-int(P["quita"])} % del precio del bono nuevo (cupón {c1(P["cupon_nuevo"])} %, 2035) a TIR UST + riesgo país. Notas (70 mil) con cupones y capital al par, sin barreras. Con Nada, los aportes del calendario quedan afuera (referencia: T-bills al {c1(a.tbill)} %). Sin margin call; las inyecciones de cobertura se informan, no se simulan. Umbrales de probabilidad con Milei y oposición con el mismo peso. Modelo de escenarios, no predicción; no es asesoramiento financiero.</p>
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
