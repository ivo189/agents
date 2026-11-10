#!/usr/bin/env python3
"""Capítulo ad hoc: el peor escenario (default y canje) para la cuenta de Cocos.
Explica cómo se modela la reestructuración, la gradúa en cuatro niveles de severidad y mide, para las tres decisiones
(Nada, Repagar caución, AO29 si RP>700), cuánto cae el patrimonio de Cocos, cuánta plata habría que inyectar y a qué precio se rompe la cuenta.
Uso: informe_peor_caso.py --dir <carpeta con base.json, w1.json, w2.json, w3.json (salidas de proyeccion_cocos.py)> --out peor_caso.html"""
import json, argparse, os, sys, html, importlib.util

ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True); ap.add_argument("--out", required=True); a = ap.parse_args()
NIV = [("base", "Base del informe"), ("w1", "Sin recuperación"), ("w2", "Canje duro"), ("w3", "Extremo")]
D = {k: json.load(open(os.path.join(a.dir, f"{k}.json"))) for k, _ in NIV}
EST = ("N", "R", "A"); NOM = {"N": "Nada", "R": "Repagar caución", "A": "AO29 si RP>700"}
HERE = os.path.dirname(os.path.abspath(__file__))

def modelo(P):
    argv = sys.argv
    sys.argv = ["x", "--quita", str(P["quita"]), "--cupon-nuevo", str(P["cupon_nuevo"]), "--canje-m", str(P["canje_m"]), "--s3-end", str(P["s3_end"]),
                "--s3-peak", str(P["s3_peak"]), "--previa", P["previa"], "--caucion-tasa", str(P["caucion_tasa"])]
    sp = importlib.util.spec_from_file_location("pc", os.path.join(HERE, "proyeccion_cocos.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    sys.argv = argv; return m
PC = {k: modelo(D[k]["parametros"]) for k, _ in NIV}
def S3(k, e): return D[k]["resultados"]["S3"]["estrategias"][e]
def px(k, b, m): return PC[k].px(b, m, PC[k].escenarios()["S3"])

def k_(v): return ("−" if v < 0 else "") + f"{abs(v)/1000:,.0f}k".replace(",", ".")
def c1(v): return f"{v:.1f}".replace(".", ",")
MESN = ["oct-26", "nov-26", "dic-26", "ene-27", "feb-27", "mar-27", "abr-27", "may-27", "jun-27", "jul-27", "ago-27", "sep-27", "oct-27", "nov-27", "dic-27",
        "ene-28", "feb-28", "mar-28", "abr-28", "may-28", "jun-28", "jul-28", "ago-28", "sep-28", "oct-28", "nov-28", "dic-28",
        "ene-29", "feb-29", "mar-29", "abr-29", "may-29", "jun-29", "jul-29", "ago-29", "sep-29", "oct-29"]

def peor(k, e):
    r = S3(k, e); w = min(r[1:], key=lambda x: x["neto"])
    return {"fecha": MESN[w["m"]], "neto": w["neto"], "cob0": max(0, -w["neto"]), "cob3": max(0, round((w["bruto"] - w["fondo"]) / 3 - w["neto"])),
            "neg": sum(1 for x in r if x["neto"] < 0), "fin": r[36]["neto"], "fin_ap": r[36]["neto_menos_aportes"], "cau_fin": r[36]["caucion"]}
def quiebre(k, e, m=12):
    """precio (por 100 de nominal) al que el neto de Cocos es cero en el mes m: (caución - notas - fondo) / nominal total."""
    r = S3(k, e)[m]; vn = r["ar"] / (px(k, "AO29", m) / 100)
    return 100 * (r["caucion"] - r["notas"] - r["fondo"]) / vn, vn, r

B = D["base"]["parametros"]; r0 = S3("base", "N")[0]
VN0 = sum(v[0] for v in PC["base"].BONOS.values())

# ---------- ejemplo numérico de la valuación ----------
T12 = PC["base"].VTO_NUEVO - PC["base"].anios(12); y12 = PC["base"].UST(T12) + B["s3_peak"] / 100
p_nuevo = PC["base"].price(y12, B["cupon_nuevo"], T12)

# ---------- tablas ----------
def t_niveles():
    t = ('<table><tr><th>Nivel</th><th>Previa</th><th>Riesgo país desde la elección</th><th>Canje</th><th>Quita del nominal</th><th>Cupón del bono nuevo</th>'
         '<th>Riesgo país en oct-29</th><th>Caución (con comisión)</th><th>Precio en oct-27</th><th>Precio en oct-29</th></tr>')
    for k, n in NIV:
        P = D[k]["parametros"]
        t += (f'<tr><td class="l"><b>{n}</b></td><td>sube a {int(P["previa"]):}</td><td class="n">{int(P["s3_peak"])} pb</td><td>{MESN[P["canje_m"]]}</td><td class="n">{int(P["quita"])} %</td>'
              f'<td class="n">{c1(P["cupon_nuevo"])} %</td><td class="n">{int(P["s3_end"])} pb</td><td class="n">{c1(P["caucion_tasa"] + P["comision_caucion"])} %</td>'
              f'<td class="n"><b>{c1(px(k, "AO29", 12))}</b></td><td class="n">{c1(px(k, "AO29", 36))}</td></tr>')
    return t + '</table><p class="note">Precio por 100 de nominal, igual para todos los soberanos desde la elección (todos van al mismo canje). Default en dic-27 en todos los niveles.</p>'

def t_resultados():
    t = ('<table><tr><th>Nivel</th><th>Decisión</th><th>Neto de Cocos en el peor mes</th><th>Meses con neto negativo</th><th>Inyección para neto ≥ 0</th>'
         '<th>Inyección para volver a 3x</th><th>Neto oct-29</th><th>Neto oct-29 menos aportes</th><th>Caución oct-29</th></tr>')
    for k, n in NIV:
        for i, e in enumerate(EST):
            p = peor(k, e)
            t += (f'<tr>{f"<td rowspan=3 class=l><b>{n}</b></td>" if i == 0 else ""}<td class="l">{NOM[e]}</td><td class="n">{k_(p["neto"])} ({p["fecha"]})</td><td class="n">{p["neg"]}</td>'
                  f'<td class="n">{k_(p["cob0"]) if p["cob0"] else "–"}</td><td class="n"><b>{k_(p["cob3"])}</b></td><td class="n">{k_(p["fin"])}</td><td class="n">{k_(p["fin_ap"])}</td><td class="n">{k_(p["cau_fin"])}</td></tr>')
    return t + '</table><p class="note">Neto de Cocos = activos a precio de mercado − caución. Con Repagar y AO29 incluye los 130 mil aportados; “menos aportes” los descuenta. Las inyecciones no se simulan: es la plata que tendrías que tener disponible en el peor mes.</p>'

def t_quiebre():
    t = '<table><tr><th>Decisión</th><th>Nominal en bonos AR</th><th>Caución en oct-27</th><th>Notas + fondo</th><th>Precio de quiebre (neto = 0)</th><th>Precio en el nivel base</th><th>Precio en el extremo</th></tr>'
    for e in EST:
        q, vn, r = quiebre("base", e)
        t += (f'<tr><td class="l">{NOM[e]}</td><td class="n">{k_(vn)}</td><td class="n">{k_(r["caucion"])}</td><td class="n">{k_(r["notas"] + r["fondo"])}</td>'
              f'<td class="n"><b>{c1(q)}</b></td><td class="n">{c1(px("base", "AO29", 12))}</td><td class="n">{c1(px("w3", "AO29", 12))}</td></tr>')
    return t + '</table><p class="note">Si los bonos valen menos que el precio de quiebre, la cuenta no cubre la caución. Con la previa que sube a 1.000.</p>'

def t_grilla():
    precios = (10, 15, 20, 25, 30, 40, 50)
    t = '<table><tr><th>Precio de los bonos (por 100)</th>' + "".join(f"<th>{p}</th>" for p in precios) + '</tr>'
    for e in EST:
        q, vn, r = quiebre("base", e)
        t += f'<tr><td class="l">{NOM[e]}</td>' + "".join(f'<td class="n">{k_(r["notas"] + r["fondo"] + vn * p / 100 - r["caucion"])}</td>' for p in precios) + '</tr>'
    return t + '</table><p class="note">Neto de Cocos en oct-27 según el precio al que queden los bonos, con la caución y las posiciones de cada decisión a esa fecha.</p>'

# ---------- gráfico: neto de Cocos en el tiempo, por nivel (rampa ordinal de un solo tono) ----------
W, H, ML, MR, MT, MB = 372, 230, 46, 70, 12, 28
RAMP = ["var(--o1)", "var(--o2)", "var(--o3)", "var(--o4)"]; DASH = ["", "", "", ""]
def panel(titulo, series, ymin, ymax):
    iw, ih = W - ML - MR, H - MT - MB
    X = lambda m: ML + iw * m / 36; Y = lambda v: MT + ih * (1 - (v - ymin) / (ymax - ymin))
    g = ""; v = ymin
    while v <= ymax + 1:
        g += f'<line x1="{ML}" x2="{W-MR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="{"zero" if v == 0 else "grid"}"/><text x="{ML-6}" y="{Y(v)+3:.1f}" class="ax" text-anchor="end">{k_(v)}</text>'
        v += 200000
    for i, t_ in enumerate(("oct-26", "abr-27", "oct-27", "abr-28", "oct-28", "abr-29", "oct-29")): g += f'<text x="{X(6*i):.1f}" y="{H-8}" class="ax" text-anchor="middle">{t_}</text>'
    g += f'<line x1="{X(12):.1f}" x2="{X(12):.1f}" y1="{MT}" y2="{MT+ih}" class="ev"/><text x="{X(12)+3:.1f}" y="{MT+9}" class="ax">elección</text>'
    ends = []
    for lab, col, vals in series:
        g += f'<path d="{"".join(("L" if i else "M") + f"{X(i):.1f},{Y(max(min(val, ymax), ymin)):.1f}" for i, val in enumerate(vals))}" fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round"/>'
        ends.append([Y(max(min(vals[-1], ymax), ymin)), lab, col])
    ends.sort()
    for i in range(1, len(ends)):
        if ends[i][0] - ends[i-1][0] < 11: ends[i][0] = ends[i-1][0] + 11
    for y, lab, col in ends: g += f'<circle cx="{W-MR}" cy="{y:.1f}" r="3" fill="{col}"/><text x="{W-MR+5}" y="{y+3:.1f}" class="lab">{lab}</text>'
    data = {"ml": ML, "iw": iw, "s": [{"l": l, "c": c, "v": v} for l, c, v in series]}
    return (f'<figure class="panel pc"><figcaption>{html.escape(titulo)}</figcaption><svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(titulo)}">{g}'
            f'<line class="cross" y1="{MT}" y2="{MT+ih}" x1="0" x2="0" style="display:none"/><rect class="hit" x="{ML}" y="{MT}" width="{iw}" height="{ih}" fill="transparent"/></svg>'
            f'<div class="tip" style="display:none"></div><script type="application/json">{json.dumps(data)}</script></figure>')
vals = [x["neto"] for k, _ in NIV for e in EST for x in S3(k, e)]
lo, hi = (min(vals) // 200000) * 200000, (max(vals) // 200000 + 1) * 200000
CORTO = {"base": "Base", "w1": "Sin recup.", "w2": "Duro", "w3": "Extremo"}
graf = '<div class="leg">' + "".join(f'<span class="lg"><svg width="30" height="10"><line x1="0" x2="30" y1="5" y2="5" stroke="{RAMP[i]}" stroke-width="3"/></svg>{n}</span>' for i, (k, n) in enumerate(NIV)) + '</div><div class="grid3">'
graf += "".join(panel(NOM[e], [(CORTO[k], RAMP[i], [x["neto"] for x in S3(k, e)]) for i, (k, _) in enumerate(NIV)], lo, hi) for e in EST) + '</div>'

# ---------- números para el texto ----------
pb, pw = peor("base", "N"), peor("w3", "N")
qN, qR, qA = (quiebre("base", e)[0] for e in EST)
ar_caida = S3("base", "N")[11]["ar"] - S3("base", "N")[12]["ar"]
P3 = D["w3"]["parametros"]

page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cocos: peor escenario</title>
<style>
:root{{--bg:#fcfcfb;--text:#0b0b0b;--muted:#52514e;--grid:#e6e5e1;--card:#fff;--line:#d6d5d0;--o1:#86b6ef;--o2:#3987e5;--o3:#1c5cab;--o4:#0d366b;--neg:#e34948}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--card:#222220;--line:#3d3c38;--o1:#1c5cab;--o2:#3987e5;--o3:#86b6ef;--o4:#cde2fb;--neg:#e66767}}}}
:root[data-theme=dark]{{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--card:#222220;--line:#3d3c38;--o1:#1c5cab;--o2:#3987e5;--o3:#86b6ef;--o4:#cde2fb;--neg:#e66767}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 Arial,Helvetica,sans-serif;padding:16px}}main{{max-width:1100px;margin:0 auto}}
h1{{font-size:21px;margin:0 0 4px}}h2{{font-size:17px;margin:30px 0 6px;border-bottom:1px solid var(--line);padding-bottom:4px}}h4{{margin:16px 0 4px;font-size:14px}}p{{margin:4px 0 8px}}
.desc,.note{{color:var(--muted)}}.note{{font-size:12px}}ul li,ol li{{margin-bottom:5px}}
.panel{{margin:8px 0;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px;position:relative}}figcaption{{font-weight:bold;font-size:12px;margin-bottom:4px}}
.grid3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
svg{{width:100%;height:auto;display:block}}.ax{{fill:var(--muted);font-size:10px}}.lab{{font-size:11px;font-weight:bold;fill:var(--text)}}
.grid{{stroke:var(--grid);stroke-width:1}}.zero{{stroke:var(--muted);stroke-width:1.2}}.ev{{stroke:var(--muted);stroke-dasharray:2 3;stroke-width:1}}.cross{{stroke:var(--muted);stroke-width:1}}
.tip{{position:absolute;top:30px;left:50px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;pointer-events:none;white-space:nowrap;z-index:2}}
.leg{{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0}}.lg{{display:inline-flex;align-items:center;gap:6px;font-size:12px;white-space:nowrap}}
table{{border-collapse:collapse;font-size:12px;margin:8px 0;display:block;overflow-x:auto}}th,td{{border:1px solid var(--line);padding:4px 7px;text-align:center;vertical-align:top}}th{{background:var(--grid)}}td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}td.l{{text-align:left}}
.steps{{counter-reset:s;list-style:none;padding:0}}.steps li{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-bottom:8px}}
.box{{border-left:4px solid var(--neg);background:var(--card);padding:8px 12px;margin:10px 0}}
</style></head><body><main>
<h1>Cocos · el peor escenario: default y canje</h1>
<p class="desc">Capítulo complementario del informe de decisión. Proyección mensual nov-26 a oct-29 con las tres decisiones: Nada, Repagar caución y AO29 si RP&gt;700.</p>

<h2>1. Por qué este capítulo</h2>
<p>En los escenarios en que se paga la deuda, las tres decisiones terminan en un rango de ~80 mil entre sí. La reestructuración es distinta: es el escenario que puede romper la cuenta. Hoy Cocos tiene {k_(r0["bruto"])} de activos, de los cuales {k_(r0["ar"])} son bonos argentinos ({VN0/1000:,.0f} mil de nominal), contra {k_(r0["caucion"])} de caución. Si los bonos caen a la zona de 25 centavos, valen ~{k_(VN0 * 0.25)}: menos que la caución. Este capítulo explica cómo se modela ese escenario, qué tan sensible es a los supuestos y cuánta plata haría falta para atravesarlo.</p>

<h2>2. Cómo se modela hoy</h2>
<ol class="steps">
<li><b>Hasta la elección (nov-26 a sep-27)</b>: igual que en los otros escenarios. Los bonos se valúan a TIR = UST + spread proporcional al riesgo país, cobran cupones (AO29 0,5 % por mes; el resto, semestral) y esos cupones repagan caución.</li>
<li><b>Elección (oct-27)</b>: el riesgo país salta a {int(B["s3_peak"])} pb. Desde ese mes el mercado deja de valuar los bonos por sus flujos originales y pasa a valuar lo que se espera recibir en el canje. Todos los soberanos valen lo mismo por 100 de nominal, porque van al mismo canje.</li>
<li><b>Default (dic-27)</b>: se suspenden todos los cupones. La caución sigue cobrando {c1(B["caucion_tasa"] + B["comision_caucion"])} % (tasa + comisión de Cocos); como no entran cupones, el interés sale del fondo o se suma a la caución. Las notas estructuradas (70 mil) siguen pagando normal.</li>
<li><b>Canje ({MESN[B["canje_m"]]})</b>: cada 100 de nominal viejo se cambia por {100-int(B["quita"])} de un bono nuevo con cupón {c1(B["cupon_nuevo"])} % semestral y vencimiento 2035. Desde ahí vuelven los cupones, que otra vez repagan caución.</li>
<li><b>Después del canje</b>: el riesgo país baja en línea recta de {int(B["s3_peak"])} a {int(B["s3_end"])} pb en oct-29, y el precio sube con él.</li>
</ol>
<h4>El precio, paso a paso (oct-27)</h4>
<p>Bono nuevo: cupón {c1(B["cupon_nuevo"])} %, vence en {c1(T12)} años. TIR = UST {c1(PC["base"].UST(T12))} % + riesgo país {c1(B["s3_peak"]/100)} % = <b>{c1(y12)} %</b>. A esa TIR, el bono nuevo vale <b>{c1(p_nuevo)}</b>. Como por cada 100 viejos recibís {100-int(B["quita"])} nuevos, el bono viejo vale {100-int(B["quita"])} % × {c1(p_nuevo)} = <b>{c1(px("base", "AO29", 12))}</b>. Ese precio es el que aparece en el informe para el AO29 y para los largos.</p>
<p class="note">Referencias históricas, de memoria y sin verificar: en el default de 2020 los bonos cotizaron en la zona de 20 a 35 centavos; en 2001-2005, la recuperación final quedó en ~25 a 35 centavos por dólar en valor presente.</p>
<h4>Lo que el modelo no captura</h4>
<ul>
<li><b>Ley local.</b> El AO29, el AL35, el AE38 y el AL41 son ley argentina. En una crisis, la deuda ley local puede recibir un trato peor (por ejemplo, una reestructuración por ley o un cambio de moneda). El modelo trata igual a todos los bonos.</li>
<li><b>Condiciones de Cocos.</b> En default, Cocos podría subir el aforo, dejar de renovar la caución o subir la tasa más allá de lo modelado. Eso adelantaría la necesidad de inyectar.</li>
<li><b>Liquidez de los bonos.</b> En default se negocian poco; vender para repagar puede costar más que el precio de pantalla.</li>
<li><b>Holdouts y demoras.</b> Un canje que se demora más de un año (como en 2001-2005) deja más meses sin cupones; el nivel “Canje duro” y el “Extremo” lo pasan a dic-28.</li>
</ul>

<h2>3. Cuatro niveles de severidad</h2>
<p>El informe de decisión usa el nivel base. Los otros tres endurecen los supuestos de a uno:</p>
{t_niveles()}
<ul>
<li><b>Sin recuperación</b>: el mismo canje, pero el riesgo país se queda en 2.000 pb hasta oct-29.</li>
<li><b>Canje duro</b>: quita del 40 %, cupón 3 %, canje recién en dic-28 (12 meses sin cupones) y riesgo país que solo baja a 1.600.</li>
<li><b>Extremo</b>: el canje duro con una previa peor (sube a 1.200), riesgo país de {int(P3["s3_peak"])} pb hasta el canje, sin recuperación y caución más cara ({c1(P3["caucion_tasa"] + P3["comision_caucion"])} %).</li>
</ul>

<h2>4. Qué le pasa a la cuenta</h2>
<div class="box">En el nivel base, la cartera de bonos pierde ~{k_(ar_caida)} en el mes de la elección. Sin capital nuevo, el neto de Cocos pasa a {k_(pb["neto"])} y queda negativo {pb["neg"]} meses. En el extremo llega a {k_(pw["neto"])} y no vuelve a ser positivo antes de oct-29.</div>
<h4>Neto de Cocos en el tiempo, por nivel de severidad</h4>
<p class="desc">Activos a precio de mercado − caución. Por debajo de la línea de cero, la cuenta no cubre la caución.</p>
{graf}
<h4>Resultados por nivel y decisión</h4>{t_resultados()}

<h2>5. El precio de quiebre</h2>
<p>La pregunta clave es a qué precio tienen que caer los bonos para que la cuenta no cubra la caución. Con las posiciones que tendría cada decisión en oct-27:</p>
{t_quiebre()}
{t_grilla()}
<p>Con Nada, la cuenta se rompe si los bonos caen por debajo de <b>{c1(qN)}</b>; repagando, por debajo de <b>{c1(qR)}</b>; con AO29, por debajo de <b>{c1(qA)}</b> (más nominal, pero también más caución). Repagar es la única decisión que mantiene la cuenta solvente en el nivel base, y aun así queda por encima del precio de quiebre por poco.</p>

<h2>6. Lectura</h2>
<ul>
<li><b>El default rompe la cuenta con cualquiera de las tres decisiones si el canje es duro.</b> Repagar caución reduce el daño pero no lo elimina: en el canje duro necesitás {k_(peor("w2","R")["cob0"])} para volver a neto cero y en el extremo {k_(peor("w3","R")["cob0"])}.</li>
<li><b>Lo que se juega es la liquidez en oct-27, no el resultado final.</b> Para volver a 3x en el peor mes harían falta, según la decisión y la severidad, entre {k_(min(peor(k,e)["cob3"] for k,_ in NIV for e in EST))} y {k_(max(peor(k,e)["cob3"] for k,_ in NIV for e in EST))}. Como cubrís el margen con dólares de afuera, la pregunta es si esa plata va a estar disponible en el momento.</li>
<li><b>AO29 es la decisión que más amplifica el default</b>: suma nominal justo en el activo que cae. En el extremo, termina {k_(abs(peor("w3","A")["fin_ap"] - peor("w3","R")["fin_ap"]))} por debajo de repagar.</li>
<li><b>Lo único que protege de verdad es bajar la exposición antes de la elección</b>: menos caución (repagar) o menos bonos (vender, por ejemplo con la regla escalonada si la previa lo permite). Después de la elección ya no hay margen de maniobra.</li>
</ul>

<h2>7. Qué mirar</h2>
<ul>
<li><b>La previa.</b> Si el riesgo país sube hacia 1.200 pb antes de la elección, el mercado empieza a valuar el default y el precio de quiebre queda más cerca.</li>
<li><b>Las encuestas en ago-sep 2027.</b> Es el último momento para bajar exposición (repagar con capital o vender parte de los largos) antes del salto.</li>
<li><b>Las condiciones de Cocos.</b> Aforos y tasa de caución en momentos de estrés; vale la pena preguntarles hoy qué hacen con la caución si un bono entra en default.</li>
<li><b>Liquidez afuera.</b> Tener identificada la plata para cubrir margen: con Nada, del orden de {k_(peor("base","N")["cob3"])} en el nivel base.</li>
</ul>
<p class="note">Modelo de escenarios, no predicción; no es asesoramiento financiero. Sin margin call: las inyecciones se informan, no se simulan.</p>
</main>
<script>
var M={json.dumps(MESN)};
document.querySelectorAll('figure.pc').forEach(function(f){{
  var d=JSON.parse(f.querySelector('script').textContent),svg=f.querySelector('svg'),hit=f.querySelector('.hit'),cr=f.querySelector('.cross'),tip=f.querySelector('.tip'),n=d.s[0].v.length;
  hit.addEventListener('mousemove',function(e){{var r=svg.getBoundingClientRect(),sc=r.width/svg.viewBox.baseVal.width,x=(e.clientX-r.left)/sc;var i=Math.max(0,Math.min(n-1,Math.round((x-d.ml)/d.iw*(n-1))));var px=d.ml+d.iw*i/(n-1);cr.setAttribute('x1',px);cr.setAttribute('x2',px);cr.style.display='';
    tip.innerHTML='<b>'+M[i]+'</b><br>'+d.s.map(function(s){{return '<span style="color:'+s.c+'">●</span> '+s.l+': USD '+Math.round(s.v[i]/1000).toLocaleString('es-AR')+' mil';}}).join('<br>');tip.style.display='';tip.style.left=Math.min(r.width-180,Math.max(4,px*sc+8))+'px';}});
  hit.addEventListener('mouseleave',function(){{cr.style.display='none';tip.style.display='none';}});
}});
</script></body></html>'''
# piezas para insertar este capítulo en el informe de decisión
CHAPTER = page[page.index("<h2>1. Por qué este capítulo</h2>"):page.index("</main>")]
JS = page[page.index("<script>", page.index("</main>")):page.index("</body>")]
CSS_EXTRA = (":root{--o1:#86b6ef;--o2:#3987e5;--o3:#1c5cab;--o4:#0d366b;--neg:#e34948}"
             "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--o1:#1c5cab;--o2:#3987e5;--o3:#86b6ef;--o4:#cde2fb;--neg:#e66767}}"
             ":root[data-theme=dark]{--o1:#1c5cab;--o2:#3987e5;--o3:#86b6ef;--o4:#cde2fb;--neg:#e66767}"
             ".zero{stroke:var(--muted);stroke-width:1.2}.steps{list-style:none;padding:0}.steps li{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-bottom:8px}"
             ".box{border-left:4px solid var(--neg);background:var(--card);padding:8px 12px;margin:10px 0}h3{font-size:15px;margin:22px 0 4px}")
open(a.out, "w").write(page)
print("ok", len(page))
