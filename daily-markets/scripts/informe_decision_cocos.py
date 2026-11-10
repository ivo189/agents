#!/usr/bin/env python3
"""Informe de decisión para la cuenta de Cocos: escenarios, alternativas y trade-offs.
Lee las salidas JSON de proyeccion_cocos.py (base y sensibilidades) y arma un HTML narrativo con tablas y un gráfico de resultados.
Uso: informe_decision_cocos.py --dir <carpeta con pc_800/1000/1200.json, pc_1000_sinrec.json, pc_1000_cau2.json, pc_1000_sinregla.json> --out informe.html
Sin margin call: si el neto de Cocos queda negativo, Ivo inyecta USD para cubrir el margen (se informa cuánto)."""
import json, argparse, os, sys, html, importlib.util

ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
L = lambda f: json.load(open(os.path.join(a.dir, f)))
B = L("pc_1000.json"); R = B["resultados"]; P = B["parametros"]
V = {k: L(f"pc_{k}.json")["resultados"] for k in ("800", "1000", "1200")}
SR, C2, SG = L("pc_1000_sinrec.json")["resultados"], L("pc_1000_cau2.json")["resultados"], L("pc_1000_sinregla.json")["resultados"]
argv, sys.argv = sys.argv, [sys.argv[0]]
sp = importlib.util.spec_from_file_location("pc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "proyeccion_cocos.py"))
pc = importlib.util.module_from_spec(sp); sp.loader.exec_module(pc); sys.argv = argv
ESC = pc.escenarios()

SC = ("S1", "S2", "S3"); BASE4 = ("N", "R", "F", "A"); EXTRA = ("M", "P"); ALL = BASE4 + EXTRA
NOM = B["estrategias"]
CORTO = {"N": "Nada", "R": "Repagar caución", "F": "Fondo USD", "A": "AO29 si RP>700", "M": "Mitad fondo / AO29", "P": "Fondo → repago sep-27"}
SCN = {"S1": "Milei reelecto", "S2": "Oposición con shock", "S3": "Reestructuración (canje)"}
def k_(v): return f"{v/1000:,.0f}k".replace(",", ".")
def sk(v): return ("+" if v >= 0 else "−") + k_(abs(v))
def x2(v): return "neto < 0" if v is None else "más de 50x" if v > 50 else f"{v:.2f}x".replace(".", ",")
def c1(v): return f"{v:.1f}".replace(".", ",")
def fin(RR, s, e): return RR[s]["estrategias"][e][36]["neto_menos_aportes"]
def row(s, e, m, RR=R): return RR[s]["estrategias"][e][m]
def nmin(s, e, RR=R): return min(r["neto"] for r in RR[s]["estrategias"][e][1:])
def lmax(s, e, RR=R):
    rr = RR[s]["estrategias"][e][1:36]; return None if any(r["lev"] is None for r in rr) else max(r["lev"] for r in rr)
def cobertura(s, e, L_=3.0, RR=R):
    """USD a inyectar en el peor mes: para neto >= 0, y para volver a L_ usando primero el fondo propio."""
    w = min(RR[s]["estrategias"][e][1:], key=lambda r: r["neto"])
    G2 = w["bruto"] - w["fondo"]
    return w["fecha"], max(0, -w["neto"]), max(0, round(G2 / L_ - w["neto"]))
def be(e, f="F", RR=R):
    """probabilidad de reestructuración a partir de la cual e deja de convenir frente a f (S1 y S2 con el mismo peso)."""
    up = (fin(RR, "S1", e) - fin(RR, "S1", f) + fin(RR, "S2", e) - fin(RR, "S2", f)) / 2
    dn = fin(RR, "S3", f) - fin(RR, "S3", e)
    return None if dn <= 0 or up <= 0 else 100 * up / (up + dn)

# ---------- gráfico: resultado oct-29 (neto menos aportes) por escenario, barras horizontales ----------
def barras(RR, ests, titulo):
    vals = [fin(RR, s, e) for s in SC for e in ests]; hi = max(vals); lo = min(0, min(vals))
    W, rowh, lab, pad = 340, 24, 150, 54
    h = f'<figure class="panel"><figcaption>{titulo}</figcaption><div class="grid3">'
    for s in SC:
        H = rowh * len(ests) + 24; iw = W - lab - pad
        X = lambda v: lab + iw * (v - lo) / (hi - lo)
        g = f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="4" y2="{H-18}" class="axis"/>'
        best = max(ests, key=lambda e: fin(RR, s, e))
        for i, e in enumerate(ests):
            v = fin(RR, s, e); y = 6 + i * rowh; x0, x1 = sorted((X(0), X(v)))
            col = "var(--s1)" if e == best else "var(--bar)"
            g += (f'<text x="{lab-6}" y="{y+13}" class="ax" text-anchor="end">{html.escape(CORTO[e])}</text>'
                  f'<rect x="{x0:.1f}" y="{y+2}" width="{max(x1-x0,1):.1f}" height="{rowh-8}" rx="3" fill="{col}"><title>{html.escape(NOM[e])}: USD {k_(v)}</title></rect>'
                  f'<text x="{(x1 if v >= 0 else x0) + (4 if v >= 0 else -4):.1f}" y="{y+13}" class="val" text-anchor="{"start" if v >= 0 else "end"}">{k_(v)}</text>')
        h += f'<div><div class="sub">{SCN[s]}</div><svg viewBox="0 0 {W} {H}" role="img" aria-label="{SCN[s]}">{g}</svg></div>'
    return h + '</div><p class="note">En azul, la mejor alternativa de cada escenario. Neto de Cocos en oct-29 menos el capital aportado.</p></figure>'

# ---------- tablas ----------
def t_precios():
    hit = [(0, "hoy"), (5, "mar-27"), (11, "sep-27"), (12, "oct-27"), (20, "jun-28"), (36, "oct-29")]
    t = '<table><tr><th>Escenario</th><th>Bono</th>' + "".join(f"<th>{l}</th>" for _, l in hit) + '</tr>'
    for s in SC:
        for i, b in enumerate(("AO29", "AL35")):
            t += (f'<tr>{f"<td rowspan=2>{SCN[s]}</td>" if i == 0 else ""}<td>{b}</td>' + "".join(f'<td class="n">{c1(pc.px(b, m, ESC[s]))}</td>' for m, _ in hit) + '</tr>')
    t += '<tr><td colspan="2">Riesgo país (pb)</td>' + "".join(f'<td class="n">{"/".join(str(int(round(R[s]["rp_path"][m]))) for s in SC) if m >= 12 else int(round(R["S1"]["rp_path"][m]))}</td>' for m, _ in hit) + '</tr>'
    return t + '</table><p class="note">Precio por 100 de nominal. En la última fila, desde oct-27: S1/S2/S3. En la reestructuración, desde la elección el precio es el del paquete del canje (75 % del bono nuevo); en jun-28 se canjea.</p>'

def t_matriz(ests):
    t = '<table><tr><th>Alternativa</th>' + "".join(f'<th>{SCN[s]}</th>' for s in SC) + '<th>Promedio simple</th><th>Peor caso</th><th>Rango</th></tr>'
    for e in ests:
        v = [fin(R, s, e) for s in SC]
        t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{k_(x)}</td>' for x in v) + f'<td class="n">{k_(sum(v)/3)}</td><td class="n">{k_(min(v))}</td><td class="n">{k_(max(v)-min(v))}</td></tr>'
    return t + '</table>'

def t_camino(ests):
    cols = [("Apal. mar-27", lambda s, e: x2(row(s, e, 5)["lev"])), ("Capacidad de compra a 2x, mar-27", lambda s, e: k_(row(s, e, 5)["capacidad_2x"])),
            ("Caución sep-27", lambda s, e: k_(row(s, e, 11)["caucion"])), ("Apal. sep-27", lambda s, e: x2(row(s, e, 11)["lev"])),
            ("Fondo disponible sep-27", lambda s, e: k_(row(s, e, 11)["fondo"])), ("AO29 / activos, mar-27", lambda s, e: f'{100*row(s, e, 5)["ao29"]/row(s, e, 5)["bruto"]:.0f} %')]
    t = '<table><tr><th>Alternativa</th>' + "".join(f"<th>{c}</th>" for c, _ in cols) + '</tr>'
    for e in ests: t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{fn("S1", e)}</td>' for _, fn in cols) + '</tr>'
    return t + '</table><p class="note">Antes de la elección los tres escenarios son iguales. Previa que sube a 1.000 pb.</p>'

def t_s3(ests):
    t = '<table><tr><th>Alternativa</th><th>Neto oct-27 (peor mes)</th><th>Apal. oct-27</th><th>Inyección para neto ≥ 0</th><th>Inyección para volver a 3x (usando antes el fondo)</th><th>Neto oct-29</th><th>Caución oct-29</th><th>Si el riesgo país no baja de 2.000: neto − aportes</th></tr>'
    for e in ests:
        f_, n0, n3 = cobertura("S3", e)
        t += (f'<tr><td class="l">{NOM[e]}</td><td class="n">{k_(nmin("S3", e))}</td><td class="n">{x2(row("S3", e, 12)["lev"])}</td><td class="n">{k_(n0) if n0 else "–"}</td>'
              f'<td class="n"><b>{k_(n3)}</b></td><td class="n">{k_(row("S3", e, 36)["neto"])}</td><td class="n">{k_(row("S3", e, 36)["caucion"])}</td><td class="n">{k_(fin(SR, "S3", e))}</td></tr>')
    return t + '</table><p class="note">La inyección no cambia el resultado económico: es capital que entra y repaga caución. Lo que cambia es cuánto tenés que tener disponible fuera de Argentina en oct-27. 3x es una referencia; tu acuerdo de margen con Cocos puede ser otro.</p>'

def t_sens(ests):
    rows_ = [("Base (caución 0,5 %, previa 1.000)", R), ("Caución a 2 %", C2), ("Sin la regla de venta de largos", SG), ("Reestructuración sin recuperación (RP 2.000)", SR)]
    t = '<table><tr><th>Sensibilidad</th><th>Escenario</th>' + "".join(f'<th>{NOM[e]}</th>' for e in ests) + '</tr>'
    for nombre, RR in rows_:
        for i, s in enumerate(SC):
            best = max(ests, key=lambda e: fin(RR, s, e))
            t += f'<tr>{f"<td rowspan=3 class=l>{nombre}</td>" if i == 0 else ""}<td class="l">{SCN[s]}</td>' + "".join(f'<td class="n">{"<b>" if e == best else ""}{k_(fin(RR, s, e))}{"</b>" if e == best else ""}</td>' for e in ests) + '</tr>'
    return t + '</table><p class="note">Neto oct-29 menos capital aportado. En negrita, la mejor de cada fila.</p>'

def t_previa(ests):
    t = '<table><tr><th>Alternativa</th>' + "".join(f'<th>Apal. sep-27, previa {k}</th>' for k in V) + "".join(f'<th>Neto − aportes S3, previa {k}</th>' for k in V) + '</tr>'
    for e in ests:
        t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{x2(V[k]["S1"]["estrategias"][e][11]["lev"])}</td>' for k in V) + "".join(f'<td class="n">{k_(fin(V[k], "S3", e))}</td>' for k in V) + '</tr>'
    return t + '</table>'

# ---------- números para el texto ----------
d = lambda s, e, f, RR=R: fin(RR, s, e) - fin(RR, s, f)
bA, bM, bAs = be("A"), be("M"), be("A", RR=SR)
cobN, cobA, cobF, cobR = cobertura("S3", "N"), cobertura("S3", "A"), cobertura("S3", "F"), cobertura("S3", "R")
salto = lambda s, b: (pc.px(b, 12, ESC[s]) - pc.px(b, 11, ESC[s]))

resumen = f'''<ul class="key">
<li><b>La decisión es, sobre todo, una apuesta a la elección de oct-27.</b> En los dos escenarios en que se paga, AO29 deja {sk(d("S1","A","F"))} contra el fondo; en la reestructuración, {sk(d("S3","A","F"))}. Con S1 y S2 con el mismo peso, AO29 conviene solo si la probabilidad de reestructuración es menor a <b>{bA:.0f} %</b> ({bAs:.0f} % si después del canje el riesgo país no baja).</li>
<li><b>El fondo USD le gana a repagar caución en los tres escenarios</b> ({sk(d("S1","F","R"))}, {sk(d("S2","F","R"))} y {sk(d("S3","F","R"))}): rinde {c1(P["fondo"])} % contra {c1(P["caucion_tasa"])} % de la caución y el canje lo capturan las dos. Repagar solo compra menor apalancamiento.</li>
<li><b>Como cubrís el margen con dólares de afuera, repagar caución pierde su principal ventaja.</b> Lo que importa en la reestructuración es cuánta plata tenés que tener disponible en oct-27: {k_(cobN[2])} con Nada, {k_(cobA[2])} con AO29, {k_(cobF[2])} con el fondo y {k_(cobR[2])} repagando (para volver a 3x).</li>
<li><b>La alternativa más flexible es el fondo</b>: mantiene el rendimiento, deja el efectivo dentro de Cocos (cubre margen sin traer plata nueva) y deja abierta la decisión hasta septiembre de 2027. Pero si querés la ganancia de la elección, hay que estar comprado antes: el AO29 salta {c1(salto("S1","AO29"))} puntos en oct-27 si gana Milei.</li>
<li><b>Mitad fondo, mitad AO29</b> queda en el medio: {sk(d("S1","M","F"))} contra el fondo si se paga y {sk(d("S3","M","F"))} en la reestructuración (umbral de {bM:.0f} %, igual que AO29 pero con la mitad de la apuesta).</li>
</ul>'''

esc_txt = f'''
<div class="card"><h4>S1 · Milei reelecto</h4><p>El riesgo país pasa de ~1.000 a <b>{int(P["s1"])} pb</b> en oct-27 y se queda ahí. El AO29 sube de {c1(pc.px("AO29",11,ESC["S1"]))} a {c1(pc.px("AO29",12,ESC["S1"]))} y los largos de ~64 a ~90. Se cumplen los tres escalones de la regla de venta (600/500/400 pb) y se venden todos los largos en oct-27 por unos {k_(row("S1","N",36)["venta_largos"])}, que repagan caución. El AO29 vence en oct-29 y la caución queda en cero en todas las alternativas.</p>
<p><b>Qué decide el resultado:</b> cuánto AO29 tenías antes de la elección. Cada 100 mil en AO29 comprados en el verano terminan unos {k_(d("S1","A","F")/row("S1","A",36)["compra_ao29"]*100000)} arriba del fondo.</p></div>
<div class="card"><h4>S2 · Oposición con shock</h4><p>El riesgo país salta a <b>{int(P["s2_peak"])} pb</b> por {P["s2_hold"]} meses y baja a {int(P["s2_end"])} pb en oct-29; la deuda se paga. El AO29 cae a {c1(pc.px("AO29",12,ESC["S2"]))} en oct-27, pero al ser corto vuelve a 100 al vencer. Los largos caen a ~51 y terminan en ~{c1(pc.px("AL35",36,ESC["S2"]))}. No se activa la regla de venta.</p>
<p><b>Qué decide el resultado:</b> igual que en S1, AO29 gana porque vence a la par en oct-29; el shock solo pesa en el camino (apalancamiento de Cocos en oct-27: {x2(row("S2","F",12)["lev"])} con el fondo, {x2(row("S2","A",12)["lev"])} con AO29, {x2(row("S2","R",12)["lev"])} repagando).</p></div>
<div class="card"><h4>S3 · Reestructuración (canje)</h4><p>Riesgo país a 2.000 pb en oct-27, default en dic-27 (sin cupones), canje en jun-28 por un bono nuevo con quita del {int(P["quita"])} % del nominal, cupón {c1(P["cupon_nuevo"])} % y vencimiento 2035. Desde la elección cada bono vale unos {c1(pc.px("AO29",12,ESC["S3"]))} centavos y sube a {c1(pc.px("AO29",36,ESC["S3"]))} en oct-29 a medida que el riesgo país baja a {int(P["s3_end"])} pb y vuelven los cupones.</p>
<p><b>Qué decide el resultado:</b> cuánto expuesto a bonos AR estás el día de la elección. La cartera pierde ~{k_(row("S3","N",11)["ar"]-row("S3","N",12)["ar"])} en un mes; con Nada y AO29 el neto de Cocos queda negativo y hay que cubrir margen.</p></div>'''

alt_txt = f'''<table><tr><th>Alternativa</th><th>Qué hace con los 130 mil</th><th>A favor</th><th>En contra</th></tr>
<tr><td class="l">Nada</td><td>No entra capital.</td><td>No compromete dólares de afuera ahora. Repagar con los 130 mil solo agrega {k_(min(d(s_,"R","N") for s_ in SC))} a {k_(max(d(s_,"R","N") for s_ in SC))} de resultado.</td><td>Apalancamiento alto todo el camino ({x2(row("S1","N",11)["lev"])} en sep-27); en la reestructuración necesitás {k_(cobN[2])} para volver a 3x.</td></tr>
<tr><td class="l">Repagar caución</td><td>Canje y repago.</td><td>El menor apalancamiento y la mayor capacidad de compra a 2x ({k_(row("S1","R",5)["capacidad_2x"])} en mar-27). Menor necesidad de cobertura en S3.</td><td>Es la que menos rinde de las tres con capital: la plata gana el 0,5 % de la caución. Irreversible: la plata queda trabada como menor deuda.</td></tr>
<tr><td class="l">Fondo USD</td><td>Canje y fondo conservador ({c1(P["fondo"])} %).</td><td>La mejor en la reestructuración y en resultado ajustado por riesgo. Líquida: puede repagar caución o comprar bonos cuando quieras.</td><td>Apalancamiento contable más alto ({x2(row("S1","F",11)["lev"])} en sep-27). Deja pasar la suba de la elección si gana Milei.</td></tr>
<tr><td class="l">AO29 si RP&gt;700</td><td>Canje y compra de AO29.</td><td>La mejor si se paga ({sk(d("S1","A","F"))} contra el fondo). TIR ~16 % y cupón mensual que repaga caución.</td><td>La peor en la reestructuración; AO29 llega al 75 % de los activos de Cocos; necesita {k_(cobA[2])} de cobertura en S3.</td></tr>
<tr><td class="l">Mitad fondo, mitad AO29 <span class="tag">variante</span></td><td>65 mil a cada uno.</td><td>Captura la mitad de la suba si se paga y conserva liquidez.</td><td>Pierde la mitad en la reestructuración; necesita {k_(cobertura("S3","M")[2])} de cobertura.</td></tr>
<tr><td class="l">Fondo y repago antes de la elección <span class="tag">variante</span></td><td>Fondo hasta sep-27; ahí el fondo repaga caución.</td><td>Le gana a repagar desde el principio en los tres escenarios ({sk(d("S1","P","R"))}, {sk(d("S3","P","R"))}) con la misma protección en la elección.</td><td>Pierde contra quedarse en el fondo ({sk(d("S3","P","F"))} en S3): una vez que cubrís margen con dólares de afuera, repagar no agrega valor.</td></tr>
</table>'''

trade = f'''
<h4>1. Retorno si se paga contra pérdida si se reestructura</h4>
<p>Contra el fondo, AO29 gana {k_(d("S1","A","F"))} en S1 y {k_(d("S2","A","F"))} en S2, y pierde {k_(-d("S3","A","F"))} en S3. Por cada dólar que puede ganar arriesga ~{c1(-d("S3","A","F")/((d("S1","A","F")+d("S2","A","F"))/2))}. El umbral de equilibrio es <b>{bA:.0f} % de probabilidad de reestructuración</b>: si creés que es menor, AO29 tiene mejor valor esperado; si es mayor, el fondo. Si la salida del canje es peor (riesgo país que no baja de 2.000), el umbral baja a {bAs:.0f} %.</p>
<h4>2. Rendimiento contra apalancamiento</h4>
<p>Repagar caución baja el apalancamiento de Cocos a {x2(row("S1","R",5)["lev"])} en mar-27 (contra {x2(row("S1","F",5)["lev"])} con el fondo) pero cuesta {k_(d("S1","F","R"))} a {k_(d("S3","F","R"))} de resultado, porque el capital queda ganando el 0,5 % de la caución en lugar del {c1(P["fondo"])} % del fondo. Si la caución sube a 2 %, la diferencia se achica a {k_(d("S1","F","R",C2))}–{k_(d("S3","F","R",C2))}, pero el fondo sigue adelante. Como vos cubrís el margen con dólares de afuera, el menor apalancamiento solo vale como comodidad, no como protección económica.</p>
<h4>3. Liquidez: cuánta plata tenés que tener en oct-27</h4>
<p>En la reestructuración, el peor mes es oct-27. Para volver a 3x (usando primero el fondo propio) necesitás {k_(cobN[2])} con Nada, {k_(cobA[2])} con AO29, {k_(cobF[2])} con el fondo y {k_(cobR[2])} repagando. Esa es la plata que tendrías que tener disponible fuera de Argentina (o en otras cuentas) justo después de la elección. La alternativa del fondo es la que menos necesita porque los 130 mil ya están adentro y líquidos.</p>
<h4>4. Concentración</h4>
<p>Hoy el AO29 es el 70 % de los activos de Cocos. Con AO29 llega a {100*row("S1","A",5)["ao29"]/row("S1","A",5)["bruto"]:.0f} %; con el fondo baja a {100*row("S1","F",5)["ao29"]/row("S1","F",5)["bruto"]:.0f} %. El fondo es la única alternativa que diversifica dentro de Cocos.</p>
<h4>5. Reversibilidad y momento de decidir</h4>
<p>El fondo es reversible: hasta sep-27 podés pasarlo a repagar caución o a AO29 según cómo venga la previa. Repagar y comprar AO29 no se deshacen sin costo. El límite: si gana Milei, el AO29 salta {c1(salto("S1","AO29"))} puntos el mes de la elección; comprar después solo captura el carry hasta el vencimiento. La ventaja de AO29 se gana estando comprado antes de la elección.</p>
<h4>6. La regla de venta de largos</h4>
<p>En S1 la regla vende todos los largos en oct-27 (el riesgo país pasa de ~1.000 a 200 de una vez). Sin la regla, el resultado en S1 sería {k_(fin(SG,"S1","F")-fin(R,"S1","F"))} mejor en todas las alternativas, porque los largos siguen subiendo después de la elección y rinden más que el 0,5 % de la caución. Es el costo de bajar la exposición a AR cuando el mercado lo permite; en S2 y S3 la regla no se activa.</p>'''

senales = f'''<ul>
<li><b>Riesgo país antes de mar-27.</b> Si baja de {int(P["umbral_ao29"])} pb mientras entran los aportes, la alternativa AO29 deja de comprar y pasa al fondo (en los caminos modelados no ocurre).</li>
<li><b>Septiembre de 2027.</b> Es el punto de decisión: con el fondo, elegir entre mantenerlo, repagar caución o pasar a AO29 según encuestas y riesgo país. En la previa que sube a 1.200 el apalancamiento con el fondo llega a {x2(V["1200"]["S1"]["estrategias"]["F"][11]["lev"])}; con Nada, a {x2(V["1200"]["S1"]["estrategias"]["N"][11]["lev"])}.</li>
<li><b>Tasa de caución.</b> Si sube cerca del {c1(P["fondo"])} % del fondo, repagar empieza a convenir; con 2 % todavía no.</li>
<li><b>Escalones de la regla de venta</b> (600/500/400 pb): avisa el email del viernes.</li>
<li><b>Liquidez afuera para oct-27</b>: tener identificados los dólares para cubrir margen en la reestructuración ({k_(cobF[2])} a {k_(cobN[2])} según la alternativa).</li>
</ul>'''

page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cocos: decisión del capital nuevo</title>
<style>
:root{{--bg:#fcfcfb;--text:#0b0b0b;--muted:#52514e;--grid:#e6e5e1;--s1:#2a78d6;--bar:#b9b8b2;--card:#fff;--line:#d6d5d0}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--s1:#3987e5;--bar:#5d5c57;--card:#222220;--line:#3d3c38}}}}
:root[data-theme=dark]{{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--s1:#3987e5;--bar:#5d5c57;--card:#222220;--line:#3d3c38}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 Arial,Helvetica,sans-serif;padding:16px}}main{{max-width:1000px;margin:0 auto}}
h1{{font-size:21px;margin:0 0 4px}}h2{{font-size:17px;margin:30px 0 6px;border-bottom:1px solid var(--line);padding-bottom:4px}}h4{{margin:14px 0 4px;font-size:14px}}p{{margin:4px 0 8px}}
.desc,.note{{color:var(--muted)}}.note{{font-size:12px}}ul.key li{{margin-bottom:6px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}}.card h4{{margin-top:0}}
.panel{{margin:8px 0;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}}figcaption{{font-weight:bold;font-size:13px;margin-bottom:6px}}
.grid3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}.sub{{font-size:12px;font-weight:bold;margin-bottom:2px}}
svg{{width:100%;height:auto;display:block}}.ax{{fill:var(--muted);font-size:11px}}.val{{fill:var(--text);font-size:11px;font-variant-numeric:tabular-nums}}.axis{{stroke:var(--muted);stroke-width:1}}
table{{border-collapse:collapse;font-size:12px;margin:8px 0;display:block;overflow-x:auto}}th,td{{border:1px solid var(--line);padding:4px 7px;text-align:center;vertical-align:top}}th{{background:var(--grid)}}td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}td.l{{text-align:left}}
.tag{{font-size:10px;border:1px solid var(--line);border-radius:4px;padding:0 4px;color:var(--muted)}}
</style></head><body><main>
<h1>Cocos · qué hacer con el capital nuevo</h1>
<p class="desc">Escenarios, alternativas y trade-offs para los 130 mil que entran entre nov-26 y mar-27. Proyección hasta oct-29 (vence el AO29), previa que sube a 1.000 pb salvo que se indique otra. Sin margin call: si el neto de Cocos queda negativo, cubrís el margen con dólares de afuera y el informe dice cuánto.</p>

<h2>En pocas palabras</h2>{resumen}
{barras(R, BASE4 + EXTRA, "Resultado en oct-29: neto de Cocos menos capital aportado (USD)")}

<h2>1. Punto de partida y premisas</h2>
<p>Posiciones del estado de Cocos del 31/10 a precios de BondTerminal del 6/11 (riesgo país 938 pb): activos {k_(row("S1","N",0)["bruto"])} (AO29 {k_(row("S1","N",0)["ao29"])}, largos {k_(row("S1","N",0)["largos"])}, notas {k_(row("S1","N",0)["notas"])}), caución {k_(row("S1","N",0)["caucion"])}, neto {k_(row("S1","N",0)["neto"])}, apalancamiento {x2(row("S1","N",0)["lev"])}.</p>
<p>Capital nuevo: 15 mil en nov-26 y dic-26, 70 mil en ene-27, 15 mil en feb-27 y mar-27. Entra desde afuera y se canjea cable a MEP con +{c1(P["gap"])} %, en todas las alternativas con capital. Los flujos de la cuenta (cupones, vencimientos de notas, venta de largos) siempre repagan caución. Caución {c1(P["caucion_tasa"])} %, fondo USD {c1(P["fondo"])} %. Rige la venta escalonada de largos (600/500/400 pb).</p>

<h2>2. Los escenarios</h2>
<div class="cards">{esc_txt}</div>
<h4>Precios supuestos</h4>{t_precios()}

<h2>3. Las alternativas</h2>
{alt_txt}

<h2>4. Resultados</h2>
<h4>Neto de Cocos en oct-29 menos capital aportado</h4>{t_matriz(ALL)}
<h4>El camino hasta la elección</h4>{t_camino(ALL)}
<h4>Reestructuración: el escenario que separa a las alternativas</h4>{t_s3(ALL)}

<h2>5. Trade-offs</h2>{trade}

<h2>6. Sensibilidades</h2>{t_sens(ALL)}
<h4>Según la previa</h4>{t_previa(ALL)}
<p class="note">La previa cambia el camino pero casi no el resultado final, porque en la elección los bonos se revalúan al nivel de cada escenario.</p>

<h2>7. Qué mirar y cuándo decidir</h2>{senales}

<h2>Supuestos y límites</h2>
<p class="note">AO29: cupón 6 % pagado 0,5 % por mes, vence oct-29. Largos: bonos sintéticos calibrados a precio y duration de BondTerminal, cupón semestral. TIR = UST + spread proporcional al riesgo país. Reestructuración: desde la elección, cada bono vale el {100-int(P["quita"])} % del precio del bono nuevo (cupón {c1(P["cupon_nuevo"])} %, 2035) a TIR UST + riesgo país. Notas (70 mil) con cupones y capital al par, sin barreras. Sin margin call ni ventas forzadas; las inyecciones de cobertura se informan, no se simulan. Las probabilidades de equilibrio tratan a S1 y S2 con el mismo peso. Modelo de escenarios, no predicción; no es asesoramiento financiero.</p>
</main></body></html>'''
open(a.out, "w").write(page)
print("ok", len(page))
