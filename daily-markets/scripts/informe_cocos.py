#!/usr/bin/env python3
"""Informe HTML del capítulo Cocos (desapalancamiento). Uso: python informe_cocos.py cocos_d.json salida.html"""
import json, sys, html
d = json.load(open(sys.argv[1])); E = d["estado_hoy"]; P = d["parametros"]
kes = lambda v: f"{v/1000:,.0f}k".replace(",", ".")
x = lambda v: ("n/d" if v is None else f"{v:.2f}x".replace(".", ","))
OP = d["opciones"]
CAM = d["caminos"]
# gráfico: 3 líneas
W, H, ML, MR, MT, MB = 600, 260, 46, 70, 14, 30
series = [("A1", "Canjear y repagar", "var(--s1)", ""), ("M", "Mixta 50/50: repagar y AO27", "var(--s2)", "7 4"), ("B1", "Canjear y comprar AO27", "var(--s3)", "2 3")]
ys = [r["lev"] for k, *_ in series for r in CAM[k]]; lo, hi = 1.2, 2.8
X = lambda m: ML + (W - ML - MR) * m / 14; Y = lambda v: MT + (H - MT - MB) * (1 - (v - lo) / (hi - lo))
g = ""
for v in (1.2, 1.6, 2.0, 2.4, 2.8): g += f'<line x1="{ML}" x2="{W-MR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/><text x="{ML-6}" y="{Y(v)+3:.1f}" class="ax" text-anchor="end">{v:.1f}x</text>'.replace(".", ",", 1) if False else f'<line x1="{ML}" x2="{W-MR}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/><text x="{ML-6}" y="{Y(v)+3:.1f}" class="ax" text-anchor="end">{str(v).replace(".", ",")}x</text>'
for m in (0, 3, 6, 9, 12, 14): g += f'<text x="{X(m):.1f}" y="{H-10}" class="ax" text-anchor="middle">{CAM["A1"][m]["fecha"]}</text>'
ends = []
for k, l, c, dash in series:
    pts = "".join(f'{"M" if i == 0 else "L"}{X(r["m"]):.1f},{Y(r["lev"]):.1f}' for i, r in enumerate(CAM[k]))
    g += f'<path d="{pts}" fill="none" stroke="{c}" stroke-width="2" {"stroke-dasharray=%s" % chr(34) + dash + chr(34) if dash else ""}/>'
    ends.append([Y(CAM[k][-1]["lev"]), l.split(":")[0].split(" ")[0] if False else {"A1": "Repagar", "M": "Mixta", "B1": "AO27"}[k], c])
ends.sort(reverse=True)
for i in range(1, len(ends)):
    if ends[i-1][0] - ends[i][0] < 12: ends[i][0] = ends[i-1][0] - 12
for yy, lab, c in ends: g += f'<circle cx="{W-MR}" cy="{yy:.1f}" r="3" fill="{c}"/><text x="{W-MR+6}" y="{yy+3:.1f}" class="lab">{lab}</text>'
chart = f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Apalancamiento de Cocos por opción">{g}</svg>'
leg = "".join(f'<span class="lg"><svg width="30" height="10"><line x1="0" x2="30" y1="5" y2="5" stroke="{c}" stroke-width="2" {"stroke-dasharray=%s" % chr(34) + dash + chr(34) if dash else ""}/></svg>{html.escape(l)}</span>' for k, l, c, dash in series)

req = '<table><tr><th>Apalancamiento objetivo</th><th>Repagar caución (USD)</th><th>Comprar activos (USD)</th><th>Relación</th></tr>' + "".join(f'<tr><td>{x(r["L"])}</td><td class="n">{kes(r["repagar_usd"])}</td><td class="n">{kes(r["comprar_usd"])}</td><td class="n">{r["comprar_usd"]/max(r["repagar_usd"],1):.1f}x más</td></tr>' for r in d["requerido"]) + '</table>'
hit = '<table><tr><th>Opción</th><th>Llega a 2,4x</th><th>2,2x</th><th>2,0x</th><th>1,8x</th><th>1,5x</th></tr>' + "".join(f'<tr><td>{html.escape(OP[k])}</td>' + "".join(f'<td>{d["hitos"][k][L]}</td>' for L in ("2.4", "2.2", "2.0", "1.8", "1.5")) + '</tr>' for k in ("A0", "A1", "M", "B1", "B2")) + '</table>'
def lev_en(k, m): return CAM[k][m]["lev"]
ruta = '<table><tr><th>Opción</th><th>hoy</th><th>ene-27</th><th>mar-27</th><th>jun-27</th><th>oct-27</th><th>dic-27</th><th>Caución dic-27</th></tr>' + "".join(f'<tr><td>{html.escape(OP[k])}</td>' + "".join(f'<td class="n">{x(lev_en(k, m))}</td>' for m in (0, 3, 5, 8, 12, 14)) + f'<td class="n">{kes(CAM[k][14]["caucion"])}</td></tr>' for k in ("A0", "A1", "M", "B1", "B2")) + '</table>'
sh = '<table><tr><th>Opción</th><th>Sin shock</th><th>Riesgo país +150 pb</th><th>+300 pb</th><th>+600 pb</th><th>Suba que lleva a 3x</th><th>a 4x</th></tr>' + "".join(f'<tr><td>{html.escape(OP[k])}</td><td class="n">{x(lev_en(k, 3))}</td>' + "".join(f'<td class="n">{x(d["shocks"][b][k][3]["lev"])}</td>' for b in ("150", "300", "600")) + f'<td class="n">+{d["colchon_bp"][k]["ene27_3x"]} pb</td><td class="n">+{d["colchon_bp"][k]["ene27_4x"]} pb</td></tr>' for k in ("A0", "A1", "M", "B1", "B2")) + '</table>'
# --- secciones nuevas (v2)
X_ = d["extras"]
brecha_t = '<table><tr><th>Par</th><th>Brecha D/C</th><th>Monto operado D (USD)</th><th>Monto operado C (USD)</th></tr>' + "".join('<tr><td>%s</td><td class="n">%s %%</td><td class="n">%s</td><td class="n">%s</td></tr>' % (k, str(v["gap_pct"]).replace(".", ","), kes(v["monto_D"]), kes(v["monto_C"])) for k, v in X_["brecha"].items()) + '</table>'
c100 = X_["comparacion_100"]
f1 = lambda v: str(v).replace(".", ",")
comp_t = ('<table><tr><th>Qué hacés con USD 100 enviados desde el exterior (hasta oct-27)</th><th>Resultado en USD</th><th>vs T-bill</th></tr>'
  '<tr><td>T-bill de EE. UU. afuera (4,1 %%)</td><td class="n">%s</td><td class="n">–</td></tr>'
  '<tr><td>AO27 con canje, <b>los dólares se quedan en Argentina</b></td><td class="n">%s</td><td class="n">+%s</td></tr>'
  '<tr><td>AO27 con canje y <b>repatriando</b> al vencer (si la brecha sigue igual)</td><td class="n">%s</td><td class="n">0,0</td></tr>'
  '<tr><td>Canje y <b>repagar caución</b> (ahorra 0,5 %% de interés)</td><td class="n">%s</td><td class="n">+%s</td></tr></table>') % (
  f1(c100["tbill_afuera"]), f1(c100["ao27_canje_queda_local"]), f1(round(c100["ao27_canje_queda_local"] - c100["tbill_afuera"], 1)),
  f1(c100["ao27_canje_repatria"]), f1(c100["repagar_caucion_canje"]), f1(round(c100["repagar_caucion_canje"] - c100["tbill_afuera"], 1)))
extra_html = ('<h3>2b. Costo real del canje: AL30C vs AL30D</h3>'
  '<p class="desc">Con tu método (precio en dólares MEP dividido por precio en cable) y las últimas operaciones de IOL del 6/11. El par AL30 tiene liquidez de sobra: opera unos USD 7,5 millones diarios en cada lado. Los precios de compra y venta no vienen en la fuente, así que no puedo medir el spread: supongo que comisiones y spread de ida y vuelta se llevan 0,5 a 1 punto, de donde sale el 5 % neto del modelo.</p>' + brecha_t +
  '<h3>2c. ¿AO27 con canje es comparable a un T-bill?</h3>'
  '<div class="box">Sí, <b>si los dólares se quedan en Argentina</b>: AO27 rinde 4,1 % y el canje suma ~5 % de una vez, unos 9,2 % hasta octubre de 2027 contra 4,0 % del T-bill. Pero hay tres cosas: (1) <b>ese beneficio también lo tenés si repagás caución</b>, así que contra la caución el AO27 gana solo la diferencia de tasas, ~3,6 % anual, con riesgo y más apalancamiento; (2) si después querés <b>repatriar</b>, el canje se devuelve y queda igual que el T-bill; (3) el AO27 opera poco, unos USD 218 mil diarios en MEP y 66 mil en cable: comprar USD 80 mil es más de un tercio del día y mueve el precio. Además vence a fin de octubre de 2027, pegado a la elección.</div>' + comp_t)
tr_html = ('<h3>3b. El tramo más expuesto es noviembre a enero</h3>'
  '<p class="desc">Respetando tu calendario, con aportes a fin de mes, los USD 80 mil entran a fin de enero y hasta entonces el apalancamiento sigue alto. Suba del riesgo país que llevaría a Cocos a 3x, mes a mes:</p>'
  '<table><tr><th>Fin de</th><th colspan="2">Canjear y repagar</th><th colspan="2">Canjear y comprar AO27</th></tr><tr><th></th><th>Apalancamiento</th><th>Suba a 3x</th><th>Apalancamiento</th><th>Suba a 3x</th></tr>' +
  "".join('<tr><td>%s</td><td class="n">%s</td><td class="n">+%d pb</td><td class="n">%s</td><td class="n">+%d pb</td></tr>' % (r["fecha"], x(r["A1"]), r["A1_bp"], x(r["B1"]), r["B1_bp"]) for r in X_["meses_expuestos"]) + '</table>'
  '<h3>3c. Opción puente: adelantar capital desde Citi o HSBC</h3>'
  '<p class="desc">Como dijiste que podés usar los ETFs de Citi o la cuenta de HSBC si cambia la necesidad de liquidez, una opción es mover capital a Cocos ahora para repagar caución y reponerlo con los aportes de enero en adelante. No es una recomendación: tiene costo de venta de los ETFs y posibles impuestos.</p>'
  '<table><tr><th>Capital movido hoy</th><th>Apalancamiento resultante</th><th>Suba del riesgo país que lleva a 3x</th></tr>' +
  "".join('<tr><td class="n">%s</td><td class="n">%s</td><td class="n">+%d pb</td></tr>' % (kes(r["X"]), x(r["lev"]), r["bp_3x"]) for r in X_["puente"]) + '</table>')
inflow = 15000 * 2 + 80000 + 20000 * 2 + 6000 * 9
page = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cocos: plan de desapalancamiento</title>
<style>:root{{--bg:#fcfcfb;--text:#0b0b0b;--muted:#52514e;--grid:#e6e5e1;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--card:#fff;--line:#d6d5d0}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1a1a19;--text:#f0efec;--muted:#c3c2b7;--grid:#34332f;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--card:#222220;--line:#3d3c38}}}}
body{{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Arial,Helvetica,sans-serif;padding:16px}}main{{max-width:980px;margin:0 auto}}h1{{font-size:20px;margin:0 0 4px}}h3{{margin:26px 0 4px;font-size:16px}}.desc{{color:var(--muted);margin:0 0 8px}}
table{{border-collapse:collapse;font-size:12px;margin:8px 0;display:block;overflow-x:auto}}th,td{{border:1px solid var(--line);padding:4px 7px;text-align:center}}th{{background:var(--grid)}}td.n{{text-align:right;font-variant-numeric:tabular-nums}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px}}svg{{width:100%;height:auto;display:block}}.grid{{stroke:var(--grid)}}.ax{{fill:var(--muted);font-size:10px}}.lab{{font-size:11px;font-weight:bold;fill:var(--text)}}
.leg{{display:flex;flex-wrap:wrap;gap:14px;margin:8px 0}}.lg{{display:inline-flex;align-items:center;gap:6px;font-size:12px;white-space:nowrap}}.box{{border-left:4px solid var(--s2);background:var(--card);padding:8px 12px;margin:10px 0}}</style></head><body><main>
<h1>Cocos · plan de desapalancamiento</h1>
<p class="desc">Precios de BondTerminal del 6/11/2026 (MEP). Posiciones del estado de cuenta de Cocos del 31/10; caución USD 460 mil. Estimación: no incluye operaciones posteriores al 31/10.</p>
<h3>Dónde estás hoy</h3>
<table><tr><th>Bonos AR (valuados hoy)</th><th>Notas BBVA/Citi (supuesto 70 mil)</th><th>Otros</th><th>Activos de Cocos</th><th>Caución</th><th>Neto de Cocos</th><th>Apalancamiento</th></tr><tr><td class="n">{kes(E["ar_usd"])}</td><td class="n">{kes(E["notas"])}</td><td class="n">{kes(E["otros"])}</td><td class="n">{kes(E["bruto"])}</td><td class="n">{kes(E["caucion"])}</td><td class="n">{kes(E["neto"])}</td><td class="n"><b>{x(E["apalancamiento"])}</b></td></tr></table>
<p class="desc">Era 2,36x al 30/10. El riesgo país pasó de 796 a 934 pb (+143 en la semana) y la cartera de bonos AR perdió unos USD 50 mil de valor. Con duration de {str(E["duration_ar"]).replace(".", ",")}, <b>una suba de unos 290 pb más llevaría a Cocos a 3x</b>.</p>
<h3>1. Cuánto hace falta: repagar caución o comprar activos</h3>
<p class="desc">Repagar baja el apalancamiento entre 2 y 3 veces más rápido que comprar activos con la misma plata (más cuanto menor el objetivo), porque comprar suma al activo y al patrimonio a la vez, y repagar solo suma al patrimonio. Capital en USD MEP, hoy.</p>{req}
<p class="desc">Si lo enviás desde el exterior y canjeás cable a MEP (brecha {P["gap"]:.0f} % neta), necesitás ~{P["gap"]:.0f} % menos de dólares: p. ej., para llegar a 2,0x repagando, USD {kes(d["requerido"][2]["desde_afuera_repagar"])} desde afuera.</p>
<h3>2. La brecha MEP/CCL: vale para las dos opciones</h3>
<div class="box">La brecha (hoy ~5,9 % bruto en BondTerminal; supongo {P["gap"]:.0f} % neta) se captura al <b>canjear dólares cable a MEP</b>, no al comprar un activo. Se aprovecha igual si con esos dólares repagás caución (Opción A1) o comprás activos (B). Con tus aportes de USD {kes(inflow)} hasta dic-27 equivale a unos <b>USD {kes(inflow * P["gap"] / 100)}</b>. Lo que sí diferencia a A de B es qué hacés con esos dólares ya canjeados.</div>
{extra_html}<h3>3. Calendario con tus aportes (nov-26 a dic-27)</h3>
<p class="desc">Aportes: 15 + 15 mil (nov-dic), 80 mil en enero, 20 + 20 mil (feb-mar) y 6 mil por mes hasta diciembre, más los cupones de lo que tenés en Cocos. Precios constantes de hoy.</p>
<div class="panel"><div class="leg">{leg}</div>{chart}</div>{ruta}{hit}
{tr_html}<h3>4. Colchón ante una nueva caída</h3>
<p class="desc">Apalancamiento de Cocos en enero de 2027 si el riesgo país subiera de golpe. Las columnas de la derecha dicen cuánto tendría que subir para llegar a 3x o 4x.</p>{sh}
<h3>5. Activos de bajo riesgo para la opción B</h3>
<table><tr><th>Activo</th><th>Precio MEP</th><th>TIR MEP</th><th>TIR en cable (con la brecha)</th><th>Duration</th><th>Comentario</th></tr>
<tr><td>AO27</td><td class="n">101,87</td><td class="n">4,09 %</td><td class="n">10,44 %</td><td class="n">0,92</td><td style="text-align:left">En MEP rinde lo mismo que un T-bill (4,1 %); con el canje y quedándose en Argentina, ~9 % hasta octubre de 2027. Opera poco y vence junto a la elección.</td></tr>
<tr><td>ON corta (Pampa Energía u otra)</td><td colspan="5" style="text-align:left">Sin datos: el listado de IOL no trae TIR ni duration de las ON. Usé un supuesto de 7 % y duration 1,5. Pasame los tickers y el precio de cada una y reemplazo el supuesto.</td></tr>
<tr><td>AO29 (lo que ya tenés)</td><td class="n">76,68</td><td class="n">16,47 %</td><td class="n">18,84 %</td><td class="n">2,47</td><td style="text-align:left">Cayó mucho, pero es lo que originó el sobregiro. Comprar más aumenta la concentración.</td></tr></table>
<h3>6. Lectura preliminar (marco, no asesoramiento financiero)</h3>
<ul><li><b>Primero repagar, después invertir.</b> Hasta bajar a ~2,0x, repagar es 2x más eficiente que comprar y el único camino que llega a 1,5x durante 2027. Con tu calendario, repagar llega a 2,0x en enero y a 1,5x hacia junio; comprar AO27 u ON llega a 2,0x en marzo y a 1,8x recién en diciembre.</li>
<li><b>El canje de la brecha conviene en ambos casos:</b> es independiente de la opción. Si la brecha se achica, mejor canjear antes que después, siempre que las reglas de Cocos lo permitan.</li>
<li><b>Una vez bajo 2,0x</b> tiene sentido analizar la opción B para lo que sobre, o la mixta, porque ahí ya hay colchón.</li>
<li><b>AO27 vs T-bill:</b> con el canje y sin repatriar, el AO27 le gana al T-bill, pero la ventaja viene del canje, que también capturás repagando caución. Lo propio del AO27 es la tasa (4,1 % contra 0,5 % de la caución) a cambio de riesgo argentino, poca liquidez y más apalancamiento.</li></ul>
<h3>Lo que necesito saber para afinar el modelo</h3>
<ul><li>Reglas de margen de Cocos: umbral de llamado, haircut por activo (bonos, ON, AO27) y si la caución se renueva sola.</li><li>Comisión real de Cocos por el canje y si hay restricción cruzada (días de espera) o impuestos.</li><li>Tickers y precios de las ON de Pampa Energía que mirás.</li></ul>
<p class="desc">Modelo de escenarios con precios constantes y shock lineal por duration; no es asesoramiento financiero.</p></main></body></html>'''
open(sys.argv[2], "w").write(page); print("ok", len(page))
