#!/usr/bin/env python3
"""Genera el informe HTML (graficos SVG interactivos + tablas) de la proyeccion de largo plazo.
Uso: python informe_largo_plazo.py --base base.json [--estres r40.json] [--notas notas.html] --out informe.html
  base.json  = salida de proyeccion_largo_plazo.py --json (caso base)
  estres.json= salida con --recovery 0.40 (opcional; agrega la tabla de estres)
  notas.html = comentario del agente (se inserta arriba; HTML simple)
Graficos: apalancamiento global, apalancamiento de Cocos, patrimonio neto (3 estrategias x 3 escenarios) y posicion AR valuada.
Paleta categorica validada (slots 1-3, all-pairs) + trazo distinto por estrategia (A solido, A2 raya, B punto)."""
import json, argparse, html

ap = argparse.ArgumentParser()
ap.add_argument("--var", action="append", required=True, help="previa=archivo.json (ej. 800=g800.json); repetible")
ap.add_argument("--estres", action="append", default=[], help="previa=archivo.json con --recovery 0.40; repetible")
ap.add_argument("--notas"); ap.add_argument("--out", required=True)
a = ap.parse_args()
VARS = {k: json.load(open(f)) for k, f in (x.split("=", 1) for x in a.var)}
ESTR = {k: json.load(open(f))["resultados"] for k, f in (x.split("=", 1) for x in a.estres)}
KEYS = list(VARS)
base = VARS[KEYS[0]]; R = base["resultados"]; estres = None
ST = [("A", "A · repagar todo", "var(--s1)", ""), ("A2", "A2 · 50% repago + 50% USA 60/40", "var(--s2)", "7 4"), ("B", "B · T-bills afuera", "var(--s3)", "2 3")]
MES = ["oct-26", "abr-27", "oct-27", "abr-28", "oct-28", "abr-29", "oct-29"]
W, H, ML, MR, MT, MB = 360, 230, 46, 40, 12, 28

def kes(v):
    return f"{v/1000:,.0f}k".replace(",", ".")
def fmt(metric, v):
    if v is None: return "n/d (neto<0)"
    return f"{v:.2f}x".replace(".", ",") if metric.startswith("lev") else f"USD {v/1000:,.0f} mil".replace(",", ".")

def panel(pid, titulo, series, metric, ymin, ymax, evento=12):
    """series: [(clave, label, color, dash, [valores m=0..36])]"""
    iw, ih = W - ML - MR, H - MT - MB
    X = lambda m: ML + iw * m / 36
    Y = lambda v: MT + ih * (1 - (v - ymin) / (ymax - ymin))
    g = ""
    span = ymax - ymin; raw = span / 4
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 10 ** (-1 if raw >= 0.1 else -2)
    step = next(m_ * mag for m_ in (1, 2, 2.5, 5, 10) if m_ * mag >= raw)
    v = (int(ymin / step) + (0 if ymin % step == 0 else 1)) * step
    while v <= ymax + 1e-9:
        y = Y(v)
        if metric.startswith("lev"): lab = f"{v:.1f}x".replace(".", ",")
        elif metric == "rp": lab = f"{v:,.0f}".replace(",", ".")
        elif abs(v) >= 1e6: lab = f"{v/1e6:.2f}M".replace(".", ",").replace(",00M", "M")
        else: lab = f"{v/1000:,.0f}k".replace(",", ".")
        g += f'<line x1="{ML}" x2="{W-MR}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="{ML-6}" y="{y+3:.1f}" class="ax" text-anchor="end">{lab}</text>'
        v += step
    for i, t in enumerate(MES):
        g += f'<text x="{X(6*i):.1f}" y="{H-8}" class="ax" text-anchor="middle">{t}</text>'
    g += f'<line x1="{X(evento):.1f}" x2="{X(evento):.1f}" y1="{MT}" y2="{MT+ih}" class="ev"/><text x="{X(evento)+3:.1f}" y="{MT+9}" class="ax">elección</text>'
    ends = []
    for k, label, col, dash, vals in series:
        d = ""; pen = False
        for m, v in enumerate(vals):
            if v is None: pen = False; continue
            d += f'{"L" if pen else "M"}{X(m):.1f},{Y(min(max(v, ymin), ymax)):.1f}'; pen = True
        g += f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" {"stroke-dasharray=%r" % dash if dash else ""}/>'.replace("'", '"')
        last = next((v for v in reversed(vals) if v is not None), None)
        if last is not None: ends.append([Y(min(max(last, ymin), ymax)), k, col])
    ends.sort(reverse=True)
    for i in range(1, len(ends)):
        if ends[i-1][0] - ends[i][0] < 11: ends[i][0] = ends[i-1][0] - 11
    for y, k, col in ends: g += f'<text x="{W-MR+4}" y="{y+3:.1f}" class="lab" fill="var(--text)">{k}</text><circle cx="{W-MR}" cy="{y:.1f}" r="3" fill="{col}"/>'
    data = {"t": titulo, "m": metric, "ml": ML, "iw": iw, "s": [{"k": k, "l": l, "c": c, "v": v} for k, l, c, d, v in series]}
    return (f'<figure class="panel" id="{pid}"><figcaption>{html.escape(titulo)}</figcaption>'
            f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(titulo)}">{g}<line class="cross" y1="{MT}" y2="{MT+ih}" x1="0" x2="0" style="display:none"/>'
            f'<rect class="hit" x="{ML}" y="{MT}" width="{iw}" height="{ih}" fill="transparent"/></svg><div class="tip" style="display:none"></div>'
            f'<script type="application/json">{json.dumps(data)}</script></figure>')

ALL = [VARS[k]["resultados"] for k in KEYS]
def grng(key):
    vs = [r[key] for RR in ALL for sc in RR.values() for e in ("A", "A2", "B") for r in sc["estrategias"][e] if r[key] is not None]
    return min(vs), max(vs)
lg0, lg1 = grng("lev_global"); lc0, lc1 = grng("lev_cocos"); n0, n1 = grng("neto")
rv = [v for RR in ALL for sc in RR.values() for v in sc["rp_path"]]
LABEL = {"800": "Previa en 800 pb (actual)", "1000": "Previa volátil: pico 1.000 pb", "1200": "Previa volátil: pico 1.200 pb"}
leg = "".join(f'<span class="lg"><svg width="30" height="10"><line x1="0" x2="30" y1="5" y2="5" stroke="{c}" stroke-width="2" {"stroke-dasharray=%r" % d if d else ""}/></svg>{html.escape(l)}</span>'.replace("'", '"') for e, l, c, d in ST)

def hitos(RR):
    CP = [(5, "mar-27"), (12, "oct-27"), (14, "dic-27"), (26, "dic-28"), (36, "oct-29")]
    t = '<table><tr><th>Escenario</th><th>Estrategia</th>' + "".join(f'<th colspan="3">{l}</th>' for _, l in CP) + '</tr><tr><th></th><th></th>' + '<th>Neto</th><th>Ap.glob</th><th>Ap.Cocos</th>' * len(CP) + '</tr>'
    for sc in ("S1", "S2", "S3"):
        for e in ("A", "A2", "B"):
            rows = RR[sc]["estrategias"][e]
            t += f'<tr><td>{sc}</td><td>{e}</td>' + "".join(f'<td class="n">{kes(rows[m]["neto"])}</td><td class="n">{(str(rows[m]["lev_global"]) if rows[m]["lev_global"] else "n/d").replace(".", ",")}x</td><td class="n">{(str(rows[m]["lev_cocos"]) if rows[m]["lev_cocos"] else "n/d").replace(".", ",")}x</td>' for m, _ in CP) + '</tr>'
    return t + '</table>'

def seccion(k):
    RR = VARS[k]["resultados"]; sm = lambda sc, e, key: [r[key] for r in RR[sc]["estrategias"][e]]
    def blk(titulo, desc, metric, key, ymin, ymax):
        x = f'<h3>{titulo}</h3><p class="desc">{desc}</p><div class="grid3">'
        for sc in ("S1", "S2", "S3"):
            x += panel(f"{k}-{metric}-{sc}", f'{sc} · {RR[sc]["nombre"]}', [(e, l, c, d, sm(sc, e, key)) for e, l, c, d in ST], metric, ymin, ymax)
        return x + "</div>"
    h = '<h3>Riesgo país supuesto (pb)</h3><p class="desc">Camino común hasta la elección (oct-2027) y desde ahí el de cada escenario. Base: BondTerminal 796 pb al 30/10/2026.</p><div class="grid3">'
    for sc in ("S1", "S2", "S3"):
        h += panel(f"{k}-rp-{sc}", f'{sc} · {RR[sc]["nombre"]}', [("RP", "Riesgo país", "var(--text)", "", RR[sc]["rp_path"])], "rp", 0, round(max(rv) / 500 + 1) * 500)
    h += "</div>"
    h += blk("Apalancamiento global (activos brutos / patrimonio neto, todas las fuentes)", "Cuánto pesa la deuda sobre el patrimonio total. 1,0x = sin deuda.", "lev_global", "lev_global", 1.0, round(lg1 + 0.1, 1))
    h += blk("Apalancamiento de la cuenta de Cocos (activos de Cocos / patrimonio neto de Cocos)", "Donde vive la caución. Sube cuando cae el precio de los bonos o no se repaga.", "lev_cocos", "lev_cocos", 1.0, round(lc1 + 0.2, 1))
    h += blk("Patrimonio neto global valuado (USD)", "Incluye aportes, cupones, rendimiento de T-bills / fondo 60/40 y la valuación de los bonos en cada escenario.", "neto", "neto", 500000, round(n1 / 100000 + 1) * 100000)
    h += '<h3>Posición en bonos soberanos AR valuada (USD)</h3><p class="desc">Valor de mercado de los bonos de Cocos. No depende de la estrategia (el AO29 vence en oct-29 y se cobra en efectivo).</p><div class="grid3">'
    for sc in ("S1", "S2", "S3"):
        h += panel(f"{k}-ar-{sc}", f'{sc} · {RR[sc]["nombre"]}', [("AR", "Bonos AR valuados", "var(--s1)", "", sm(sc, "A2", "ar"))], "ar", 0, 1000000)
    return h + f'</div><details><summary>Ver tabla por hitos (datos de los gráficos)</summary>{hitos(RR)}</details>'

def tabla_riesgo():
    t = '<table><tr><th rowspan="2">Escenario</th><th rowspan="2">Estrategia</th><th rowspan="2">Neto oct-29</th>' + f'<th colspan="{len(KEYS)}">Apalancamiento máx. de Cocos (nov-26 a sep-29)</th><th colspan="{len(KEYS)}">Neto de Cocos mínimo</th></tr><tr>' + "".join(f"<th>previa {k}</th>" for k in KEYS) * 2 + '</tr>'
    for sc in ("S1", "S2", "S3"):
        for e in ("A", "A2", "B"):
            fin = VARS[KEYS[0]]["resultados"][sc]["estrategias"][e][36]["neto"]
            lc = [max((r["lev_cocos"] or 99) for r in VARS[k]["resultados"][sc]["estrategias"][e][1:36]) for k in KEYS]
            cn = [min(r["cocos_neto"] for r in VARS[k]["resultados"][sc]["estrategias"][e][1:36]) for k in KEYS]
            t += f'<tr><td>{sc}</td><td>{e}</td><td class="n">{kes(fin)}</td>' + "".join(f'<td class="n">{str(round(x, 2)).replace(".", ",")}x</td>' for x in lc) + "".join(f'<td class="n">{kes(x)}</td>' for x in cn) + '</tr>'
    return t + '</table>'

def tabla_estres():
    if not ESTR: return ""
    t = '<h3>Estrés del escenario 3: recupero del 40% del nominal tras el canje</h3><table><tr><th rowspan="2">Estrategia</th><th rowspan="2">Neto oct-29</th>' + f'<th colspan="{len(ESTR)}">Neto de Cocos mínimo</th></tr><tr>' + "".join(f"<th>previa {k}</th>" for k in ESTR) + '</tr>'
    k0 = next(iter(ESTR))
    for e in ("A", "A2", "B"):
        t += f'<tr><td>{e}</td><td class="n">{kes(ESTR[k0]["S3"]["estrategias"][e][36]["neto"])}</td>' + "".join(f'<td class="n">{kes(min(r["cocos_neto"] for r in ESTR[k]["S3"]["estrategias"][e][1:36]))}</td>' for k in ESTR) + '</tr>'
    return t + '</table>'

tabs = "".join(f'<button class="tab{" on" if i == 0 else ""}" data-v="{k}">{LABEL.get(k, k)}</button>' for i, k in enumerate(KEYS))
secs = "".join(f'<section class="var" id="v-{k}" style="{"" if i == 0 else "display:none"}">{seccion(k)}</section>' for i, k in enumerate(KEYS))
notas = open(a.notas).read() if a.notas else ""
P = base["parametros"]
page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Proyección de largo plazo</title>
<style>
:root{{--bg:#fcfcfb;--text:#0b0b0b;--muted:#52514e;--grid:#e6e5e1;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--card:#fff;--line:#d6d5d0}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--card:#222220;--line:#3d3c38}}}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Arial,Helvetica,sans-serif;padding:16px}}main{{max-width:1100px;margin:0 auto}}
h1{{font-size:20px;margin:0 0 4px}}h3{{margin:26px 0 2px;font-size:16px}}.desc{{color:var(--muted);margin:0 0 8px}}
.grid3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}}
.panel{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px;position:relative}}figcaption{{font-weight:bold;font-size:12px;margin:0 0 2px}}
svg{{width:100%;height:auto;display:block}}.grid{{stroke:var(--grid);stroke-width:1}}.ax{{fill:var(--muted);font-size:10px}}.lab{{font-size:11px;font-weight:bold}}.ev{{stroke:var(--muted);stroke-dasharray:2 3;stroke-width:1}}.cross{{stroke:var(--muted);stroke-width:1}}
.tip{{position:absolute;top:30px;left:50px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;pointer-events:none;white-space:nowrap}}
.leg{{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0}}.lg{{display:inline-flex;align-items:center;gap:6px;font-size:12px;white-space:nowrap}}
.tabs{{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}}.tab{{border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:6px;padding:6px 10px;cursor:pointer;font-size:13px}}.tab.on{{background:var(--text);color:var(--bg)}}
table{{border-collapse:collapse;font-size:12px;margin:8px 0;display:block;overflow-x:auto}}th,td{{border:1px solid var(--line);padding:4px 6px;text-align:center}}th{{background:var(--grid)}}td.n{{text-align:right;font-variant-numeric:tabular-nums}}
details{{margin-top:14px}}.foot{{color:var(--muted);font-size:12px;margin-top:18px}}
</style></head><body><main>
<h1>Proyección de largo plazo · nov-2026 a oct-2029</h1>
<p class="desc">3 escenarios de resultado electoral × 3 caminos de riesgo país previo a la elección × estrategias. Punto de partida: neto global USD 666 mil, caución USD 460 mil, apalancamiento global 1,69x y de Cocos 2,37x.</p>
{notas}
<div class="leg">{leg}</div>
<div class="tabs" role="tablist" aria-label="Camino del riesgo país antes de la elección">{tabs}</div>
{secs}
<h3>Riesgo y retorno por estrategia y camino previo</h3><p class="desc">El patrimonio final no depende del camino previo (no hay ventas forzadas en el modelo); sí cambian el apalancamiento máximo de Cocos y su patrimonio neto mínimo.</p>{tabla_riesgo()}
{tabla_estres()}
<p class="foot">Supuestos: riesgo país 796 pb al inicio; tres caminos previos hasta sep-27 (800 constante, pico 1.000, pico 1.200); desde oct-27 cada escenario fija el suyo: S1 {int(base["resultados"]["S1"]["rp_path"][12])} pb, S2 {int(P["s2_peak"])} pb por {P["s2_hold"]} meses y luego baja linealmente a {int(P["s2_end"])} pb en oct-29 (paga todo), S3 2.000 pb con cupones suspendidos desde dic-27 y bonos a valor {"implícito en el riesgo país" if P["recovery"] < 0 else str(int(P["recovery"]*100)) + "% del nominal"}. TIR = UST + spread proporcional por bono; AO29 con cupón mensual 0,5% y flujos reales; resto de soberanos como bonos sintéticos con cupón semestral (ene/jul); notas de Cocos (70 mil, 3 notas) con cupones y capital al par; T-bills {P["tbill"]}%, caución {P["caucion_tasa"]}%, fondo USA 60/40 {P["ret_acc"]}% / {P["ret_rf"]}% (esperado, sin volatilidad), otros activos {P["ret_otros"]}%. Modelo de escenarios, no predicción; no es asesoramiento financiero.</p>
</main>
<script>
document.querySelectorAll('.tab').forEach(function(b){{b.addEventListener('click',function(){{document.querySelectorAll('.tab').forEach(function(x){{x.classList.toggle('on',x===b)}});document.querySelectorAll('section.var').forEach(function(s){{s.style.display=(s.id==='v-'+b.dataset.v)?'':'none'}});}});}});
document.querySelectorAll('figure.panel').forEach(function(f){{
  var d=JSON.parse(f.querySelector('script').textContent),svg=f.querySelector('svg'),hit=f.querySelector('.hit'),cr=f.querySelector('.cross'),tip=f.querySelector('.tip');
  var n=d.s[0].v.length,MES=['nov-26','dic-26','ene-27','feb-27','mar-27','abr-27','may-27','jun-27','jul-27','ago-27','sep-27','oct-27','nov-27','dic-27','ene-28','feb-28','mar-28','abr-28','may-28','jun-28','jul-28','ago-28','sep-28','oct-28','nov-28','dic-28','ene-29','feb-29','mar-29','abr-29','may-29','jun-29','jul-29','ago-29','sep-29','oct-29'];
  function f2(m,v){{if(v===null)return 'n/d (neto<0)';if(m==='rp')return Math.round(v)+' pb';if(m.indexOf('lev')===0)return v.toFixed(2).replace('.',',')+'x';return 'USD '+Math.round(v/1000).toLocaleString('es-AR')+' mil';}}
  hit.addEventListener('mousemove',function(e){{var r=svg.getBoundingClientRect(),sc=r.width/svg.viewBox.baseVal.width,x=(e.clientX-r.left)/sc;var i=Math.max(0,Math.min(n-1,Math.round((x-d.ml)/d.iw*(n-1))));var px=d.ml+d.iw*i/(n-1);cr.setAttribute('x1',px);cr.setAttribute('x2',px);cr.style.display='';
    tip.innerHTML='<b>'+(i===0?'oct-26 (hoy)':MES[i-1])+'</b><br>'+d.s.map(function(s){{return '<span style="color:'+s.c+'">●</span> '+s.k+': '+f2(d.m,s.v[i]);}}).join('<br>');tip.style.display='';tip.style.left=Math.min(r.width-190,Math.max(4,px*sc+8))+'px';}});
  hit.addEventListener('mouseleave',function(){{cr.style.display='none';tip.style.display='none';}});
}});
</script></body></html>'''
open(a.out, "w").write(page)
print("ok", len(page))
