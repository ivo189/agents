# Agente semanal: patrimonio consolidado, notas estructuradas, curva soberana AR

Corre **una vez por semana, viernes por la tarde** (después del cierre de NYSE y BYMA; sugerido
viernes 16:30 hora Ciudad de México = 19:30 ART). Es una revisión para decidir, no un parte diario:
priorizá **cambios de la semana** (viernes a viernes) sobre fotos del día. Español rioplatense, directo.
Un solo email HTML a ivo.airasca.porta@gmail.com con asunto `Reporte semanal DD/MM – Patrimonio, notas y curva AR`.
Semanal significa: variación 5 ruedas (OHLCV 1D, últimas 6 barras) de subyacentes y bonos; evolución del
riesgo país (`sparklineData`) y de la TIR; carry devengado en la semana; P&L semanal por fuente;
qué observaciones/pagos/vencimientos caen en los próximos 14 días; y al final **"Puntos a decidir"**:
umbrales o eventos que se acercan (no recomendaciones de compra/venta salvo que Ivo las pida).
No sos asesor financiero: no recomiendes comprar/vender salvo que Ivo lo pida.

## Parte 0 – Patrimonio consolidado (todas las fuentes)
Fuentes principales (config en `fuentes.json`): Cocos (Parte 3), IBKR, Citi (2 brokerage + 1 checking),
HSBC US, HSBC MX (fondos, MXN). Hay otras minoritarias que Ivo no lista: no inventar, decir "no incluidas".
1. **IBKR**: conector (`get_account_summary`, `get_account_positions`, `get_account_balances`), solo lectura.
2. **Citi / HSBC US / HSBC MX** (ids en `fuentes.json`; listar con `search_files` y query `parentId = '<id>'`;
   los PDFs bajan con `download_file_content` en base64 -> decodificar a archivo y correr `scripts/parse_netx.py`;
   nombre `<cuenta>_<DDMMAAAA>.pdf`; HSBC MX es un Google Sheet, columna H en MXN, leer con Sheets `get_values`): estados de cuenta PDF en carpetas de Drive (ids en `fuentes.json`);
   tomar el más reciente de cada cuenta, leerlo con el conector de Drive, extraer posiciones, cash y
   fecha de corte. Si no hay carpeta/archivo, decirlo y usar el último dato conocido marcándolo.
3. Normalizar todo a un JSON y correr `scripts/consolidar.py` (FX: USD/MXN y ARS MEP del día, EUR→USD; la fuente
   de FX se cita). Cocos va con su `pasivos` (caución) para el neto real.
4. Reportar: patrimonio bruto/pasivos/neto en USD, % por fuente, clase y moneda, top 10, **exposición por
   subyacente** (MELI y NU aparecen en IBKR + notas BBVA/Citi + Cocos: sumarlas con `expo`), moneda
   (ARS/MXN/EUR/USD) y riesgo país/soberano AR sobre el neto.
5. **Antigüedad**: si un estado de cuenta tiene > 10 días, marcarlo arriba. Si no se pudo leer una fuente,
   el total es parcial y hay que decirlo en el titular. Los datos de cuentas son sensibles: ni números de
   cuenta ni CUIT/SSN en el email; no commitear estados de cuenta al repo.
5b. **Inputs manuales** (`inputs_manuales` en `fuentes.json`): sumarlos como posiciones, rotulados "manual" con su fecha; si el Sheet de la fuente ya trae esa posición (p.ej. cuenta a la vista de HSBC MX), usar el Sheet y NO duplicar.
6. **Riesgo país / concentración**: exposición por país económico (no por moneda de cotización: los bonos AR en USD
   cotizan en ARS pero son riesgo USD-soberano AR). Reportar Argentina soberano + corporativo (p.ej. PAM) como % del bruto y
   del NETO; EE.UU., Brasil/LatAm, México, Europa, EM, global. **Apalancamiento global** = bruto/neto con todas las
   fuentes (hoy la única deuda es la caución de Cocos). Las notas BNP de Citi (cuenta 2245: MS, SOXX, GS) tienen precio de
   mercado en el estado: usarlo como valuación y compararlo con el payoff del skill. Las notas BBVA en Cocos pueden
   tener precio desactualizado (marca `***`): avisarlo. "Otros minoritarios" ~USD 15.000: se informan aparte, sin detalle.
7. Fondos HSBC MX: valor en MXN, rendimiento de la semana si el estado lo trae, y convertir a USD; no
   asumir TIR ni composición si no están en el estado.

## Prioridad y control de calidad (leer primero)
- Orden de prioridad si falta tiempo/contexto: (1) patrimonio consolidado + concentración, (2) notas + riesgos,
  (3) cartera Cocos + apalancamiento, (4) curva, (5) proyección de volumen, (6) vol realizada. Mandá igual el email y declarar lo omitido.
  Para no quedarte corto: traé OHLCV con `summary=true` cuando solo necesites agregados, y armá un único
  JSON por script (volumen y cierres de todos los tickers) en vez de una corrida por ticker.
- **Saneá datos de TradingView**: descartá precios ≤ 0, volúmenes absurdos (> 1e12) o series vacías
  (pasa con `BCBA:AO29`/`AO29D`: devuelve negativos y volumen 1e100). En ese caso usá el precio del PDF
  de Cocos, aclaralo y no proyectes volumen de ese bono.
- **Riesgo país**: tomalo del texto/tabla de la fuente (nunca de un slug o número de la URL) y confirmalo
  con una segunda fuente; si difieren > 15 pb, informá ambos.
- **TIR**: usar UNA sola fuente por día para todos los bonos (misma base: TIR en USD sobre precio MEP,
  efectiva anual) y decir cuál es. No mezclar fuentes ni comparar AL vs GD si la base no es la misma.
  Es orden de magnitud: si dos fuentes difieren > 100 pb para el mismo bono, avisarlo en el mail.
- **Caución USD**: usar la tasa de `cocos_cauciones.json` (informada por Ivo, ~2%). No compararla con la
  caución en pesos (otra moneda); no hace falta buscar una tasa USD pública.

## Parte 1 – Notas estructuradas
1. Invocá el skill `estado-notas-estructuradas` y seguí su procedimiento tal cual (fecha = hoy en
   America/Argentina/Buenos_Aires; precios de los 8 tickers MS, SOXX, GS, MSFT, ORCL, MELI, NU, BBD).
   Preferí TradingView (`mcp-tv-get-ohlcv`, `get-symbol-data-batch`); fallback IBKR.
2. Contra el **precio actual** (último cierre/pre-market), por nota: nivel worst-of vs inicial (%),
   colchón en pp a barrera de cupón y de capital, y a autocall; próxima observación y días que faltan.
3. **Riesgos**: nota a < 15 pp de barrera, cupón en riesgo en la próxima observación, concentración
   MELI/NU (nominal total expuesto), correlación/divergencia entre subyacentes de las worst-of,
   volatilidad realizada 20d vs 60d (`scripts/realized_vol.py`, cierres de ≥ 61 ruedas). Lo sorprendente va arriba.
4. **Proyección de volumen** de los 8 subyacentes: traé ≥ 21 ruedas de volumen (OHLCV 1D), armá un
   JSON `{"MELI":[...],...}` en el scratchpad y corré `daily-markets/scripts/volume_projection.py
   input.json [TICKER=fecha_observacion]`. Informá volumen último día, ratio vs mediana 20d,
   proyección y banda de la próxima rueda; marcá los que tengan observación/evento en ≤ 5 días.
   Aclarar que es una estimación estadística simple.
5. Tabla resumen de las 6 notas + próximas fechas (60 días) + exposición por subyacente.

## Parte 2 – Curva soberana argentina (USD, ley NY y local)
1. Bonos: GD29, GD30, GD35, GD38, GD41, GD46 (referencia: AL30/AL35/AE38/AL41). Precio, variación
   diaria/semanal y **volumen** de cada uno: `mcp-tv-get-ohlcv` sobre `BCBA:<ticker>D` (cotización
   MEP; el sufijo D es USD). Si falta alguno, decilo.
2. **Fuente primaria (BondTerminal, ya habilitada en la red del entorno):** `curl -s
   "https://bondterminal.com/api/landing/sovereign?basis=mep"` devuelve JSON con `sections[].bonds[]`:
   `ticker` (sufijo D = USD MEP), `price` (USD por 100 VN), `changePercent1D`, `ytm`, `modDuration`,
   `gSpread` (pb), `amountOutstanding`; incluye GD29/30/35/38/41/46, AL29/30/35, AE38, AL41, AO27/28/29,
   AN29. Riesgo país: `.../api/landing/riesgo` (`valueBps`, `deltas`, serie `sparklineData`, y `ambitoValue`
   como contraste). Es una sola fuente y una sola base (MEP), así que las TIR son comparables entre bonos.
   Usá `asOfDisplay`/`curveDate` para informar la fecha del dato. Son endpoints públicos de la página; los
   términos de BondTerminal mencionan una API con claves y límites: hacer pocas llamadas por día (1-3) y,
   si Ivo consigue una API key, pasar a esa. Si falla, caer a TradingView (precio/volumen) + WebSearch.
   Para AO29 (TradingView no sirve) tomá precio y TIR de BondTerminal.
   (Antiguo, solo fallback) TIR, duration y paridad: no están en TradingView. Obtenelas con WebSearch de fuentes públicas
   (Bonistas, Rava, Ámbito, IAMC) y citá la fuente y hora. **No inventes TIRs**: si no conseguís
   un dato, dejalo vacío y avisá. También riesgo país (EMBI JPM) y, si hay, dólar MEP/CCL y brecha.
   (Los hosts de APIs directas están bloqueados en el sandbox; usar WebSearch.)
3. Armá `curve.json` (formato en el docstring de `scripts/curve_math.py`) y corré el script con
   `--prev` si tenés el del día anterior. Reportá: forma de la curva, pendiente, tramos invertidos,
   butterfly, cambio en pb vs ayer, riesgo país, y lectura breve (qué se mueve y por qué, con noticias
   relevantes encontradas: BCRA, FMI, vencimientos, licitaciones del Tesoro).
4. **Proyección de volumen** de los bonos: mismo método (`volume_projection.py`) sobre volumen
   operado; marcar si hay pago de cupón/amortización (9-ene/9-jul) o licitación próxima.
5. Opcional si hay datos: curva en pesos (LECAP/CER/duales) en una sección corta.

## Parte 3 – Cartera real en Cocos Capital
1. Fuente: el PDF "Resumen de cuenta" más reciente (`portfolio_report_YYYYMMDD.pdf`) en la carpeta de
   Drive "Portfolio Cocos" (id `1orsb0zscqQiZasaRG5m1RXjjrPhwLTe0`). `search_files` no filtra por carpeta:
   buscá `title contains 'portfolio_report'` y quedate solo con resultados cuyo `parentId` sea ese id y
   mimeType PDF; elegí la fecha más nueva del nombre. Leé el texto con `read_file_content`/`download_file_content`.
   Ignorá copias .csv/.sheet fuera de la carpeta: el PDF (CNV) es la fuente de verdad.
   Si no hay Drive, usar el último que Ivo haya subido a la sesión.
2. Parsear con `scripts/parse_cocos.py reporte.pdf` (pdftotext). Verificar que la suma coincida con
   "Total Posición". Nunca copiar CUIT/comitente al email ni al repo; el PDF no se commitea.
3. Avisar la **antigüedad** de la tenencia (fecha de posición vs hoy). Si tiene > 7 días, decirlo
   arriba del reporte: los pesos y P&L pueden estar desactualizados.
4. Cruzar con la curva: valuar cada bono con su precio actual (los precios del PDF son ARS cada
   100 VN), peso en cartera, TIR y duration ponderadas de la cartera soberana, concentración por
   bono/tramo (hoy AO29 ~70%), exposición USD vs ARS, y qué tramo de la curva te pega más si se
   mueve +/-100 pb. Las notas BBVA aparecen en Cocos; las de BNP y Citi no (se ven con el skill).

### Apalancamiento / caución
El PDF NO lista la caución como instrumento. Aparece como "Posición pendiente de liquidación"
(negativa, ARS -721 M al 31/10) y "RESULTADO" engañoso; el parser la devuelve en `apalancamiento`.
Patrimonio neto = Total Posición + pendiente (≈ ARS 531 M); bruto/neto ≈ 2,36x. Reportá:
- neto vs bruto y apalancamiento; peso de cada bono sobre el **neto**.
- La caución de Ivo es **en USD** (tasa ~2% anual según Ivo; AO29 rinde ~8%): deuda USD = pendiente ARS /
  MEP del PDF. No hay descalce de moneda con los bonos USD; el riesgo es precio, tasa de renovación y garantías.
  Carry = (TIR cartera bonos - tasa caución USD) en pb, en USD/día y como % del patrimonio neto.
  **Tasa de caución USD (variable):** buscar la tasa a 1 día vigente en una fuente de cauciones en dólares
  (correr `python3 -I daily-markets/scripts/caucion_usd.py`: lee IOL, fila DOLARES de plazo más corto; los viernes el "1 día" es plazo 3; si falla, WebSearch). Informar fecha y
  fuente. Si no se consigue dato del día, usar `tasa_anual_pct` del archivo y rotularla "referencia fija
  (2%), no actualizada". Nunca inventar la tasa.
- sensibilidad: caída de -5/-10/-15% en los bonos => % de caída del patrimonio neto (≈ apalancamiento x caída).
- Margin call: Ivo tiene acuerdos de margen con Cocos y su plan es esperar la recuperación del AO29
  mientras devenga. NO lo marques como alerta ni insistas; la sensibilidad a caídas es solo informativa.
- P&L no realizado: costo de AO29 = 95 (USD por 100 VN, según Ivo) vs precio de hoy; mostrar también
  TIR de entrada (~8%) vs TIR actual, y el carry diario devengado vs caución.
No interpretes el RESULTADO del PDF como pérdida: mezcla aportes y pendiente.

## Parte 5 – Dónde alocar futuros ahorros
Capítulo del email (después de volumen, antes de calidad de datos). Insumos: `politica_inversion.json` (flujos de ahorro,
límites propuestos, pendientes por confirmar) y el estado consolidado de la Parte 0.
1. Recalcular con datos frescos: neto, bruto, caución, AR soberano (USD), TIR de la cartera AR, tasa de caución USD
   (`caucion_usd.py`), tasa libre de riesgo (T-bill 3M / UST 2Y / 10Y de TradingView `TVC:US03MY`, `TVC:US02Y`, `TVC:US10Y`).
2. Correr `scripts/asignacion.py` con `flujo` = ahorro acumulado pendiente (hoy USD 130.000 a fin de enero 2027:
   10.000 en nov, dic y ene + ~100.000 extra en enero) y mostrar los escenarios A (repagar caución), B (diversificar fuera de AR),
   C (mixto), D (más soberano AR, solo referencia) con neto, apalancamiento, % AR sobre neto, pérdida ante shock AR y delta de carry.
3. Contrastar con los límites de `politica_inversion.json` y decir cuáles se cumplen/violan en cada escenario.
4. Cronograma: qué ahorro ya entró (comparar con el flujo previsto) y cuál es el siguiente tramo; evitar mover plata sin costo/sentido.
5. Marco, no orden: sin lenguaje de "comprá/vendé"; explicar trade-offs (p. ej. repagar caución al 0,5% rinde poco pero baja
   riesgo; D tiene más carry pero no diversifica). Cerrar con "no es asesoramiento financiero; decide Ivo" y listar los datos
   pendientes de confirmar (horizonte, colchón de liquidez, tolerancia a caída, costos de traslado, fiscalidad).
5b. Horizonte de Ivo: 3 años (≈ nov-2029); liquidez inmediata no requerida, reserva secundaria = ETFs de Citi + HSBC (≈ USD 205 mil, ver política). Por eso el ahorro nuevo no necesita quedar en caja ociosa; comparar opciones con vencimiento ≤ 3 años (T-bills, UST 2Y 4,6%) y notar que el AO29 vence dentro del horizonte (31-oct-2029). Si el horizonte o la liquidez cambian, Ivo edita `politica_inversion.json`.
6. Si cambian los flujos reales, Ivo edita `politica_inversion.json`; el agente no inventa ahorros no declarados.

## Parte 6 – Serie de tiempo del apalancamiento (semanal)
Cada corrida agrega UNA fila a la planilla "Evolucion Ratio apalncamiento" (id en `fuentes.json` -> `serie_apalancamiento`;
hoja `Hoja 1`) y la incluye en el email. Es el único registro histórico: las sesiones del agente son efímeras, así que
la planilla es la memoria entre semanas.
1. Leer `'Hoja 1'!A:M` con `get_values`. Si ya existe una fila con la misma fecha de corte, NO duplicar: actualizarla.
2. Con los números de la Parte 0 y 3 armar la fila con `scripts/serie_apalancamiento.py` (fecha = viernes de corte;
   bruto global y neto global del consolidado; caución USD; bruto Cocos; AR soberano en USD; MEP; riesgo país BondTerminal)
   y escribirla con `update_formulas` en la primera fila vacía (columnas D, E, G, H, J son fórmulas: no pegar valores).
   Apalancamiento = activos brutos / patrimonio neto; global = todas las fuentes; Cocos = bruto Cocos / (bruto Cocos − caución).
   En la columna M escribir fuente y antigüedad de los datos (p. ej. "Cocos 31-oct, Citi 1-nov"); si falta una fuente, decirlo.
3. Verificar leyendo la fila de nuevo (neto > 0, ratios plausibles). Si la deuda aparece fuera de Cocos (p. ej. margen en IBKR),
   no cambiar la definición en silencio: avisarlo en el email y en la nota de la fila.
4. En el email: tabla de las últimas 12 semanas (fecha, apalancamiento global, apalancamiento Cocos, neto global, riesgo país),
   variación vs semana anterior (en x y %), vs la primera fila y mínimo/máximo del período, más el link a la planilla. Si hay
   una sola fila, decir que la serie recién empieza. El gráfico de líneas vive en la planilla (celda O1); no se embebe en el mail.
5. Los datos históricos no se reescriben: si un dato viejo estaba mal, agregar una nota en M, no borrar la fila.

## Parte 7 – Proyección de largo plazo (semanal)
Modelo `scripts/proyeccion_largo_plazo.py` (supuestos en `plan_largo_plazo.json`, anclado al estado del 30-oct-2026): 3 escenarios de
riesgo país (300 / 1000 / 2000 pb con default) x estrategias A, A2 (50% repago + 50% USA 60/40; cupones y vencimientos repagan caución),
A4 (A2 + vender bonos largos) y B (T-bills afuera), mensual hasta oct-2029. Cupones: AO29 mensual 0,5%; resto de soberanos semestral
(ene/jul); notas de Cocos (70.000 en 3 notas) por term sheet. Las gráficas viven en la pestaña "Proyección LP" del Google Sheet de
apalancamiento (id en `fuentes.json` -> `serie_apalancamiento`; gid 777), con 10 gráficos nativos que se actualizan solos al reescribir los datos.
Cada semana:
1. Leer de la pestaña la fila del mes en curso (`get_values` de `'Proyección LP'!A:AK`) y comparar el apalancamiento global, el de Cocos y el
   patrimonio neto REALES (Parte 0/3/6) contra A, A2 y B de cada escenario: "real vs proyectado" y a qué estrategia se parece el camino real.
2. En el email, sección "Proyección de largo plazo": tabla de hitos (oct-27, dic-27, oct-29) por escenario y estrategia (neto, apalancamiento
   global y de Cocos), tabla de riesgo-retorno (neto final en S1/S2/S3, apalancamiento de Cocos máximo y neto de Cocos mínimo tras la elección,
   estrés con recupero 40%), el costo de la protección (A, A2 vs B) y el link a la pestaña con las gráficas
   (https://docs.google.com/spreadsheets/d/1Cf2ia_4LHchQl2a2aNR1aiCQei3rPkBfTqQr5Xpc6Qg/edit#gid=777). No pegar gráficos en el mail (se pierden).
3. Reproducir/refrescar: `python3 -I scripts/proyeccion_largo_plazo.py --json > base.json` y, si cambió algún supuesto (aportes, tasas,
   caución, composición de notas, bonos) o el estado real se desvía > 5% del camino proyectado, correr `scripts/proyeccion_a_sheet.py base.json`
   y reescribir la pestaña con `update_formulas` (el rango y el formato salen del script; los gráficos no se tocan). Informe HTML interactivo
   completo: `scripts/informe_largo_plazo.py --base base.json --estres r40.json --out informe.html` (a pedido de Ivo; no adjuntar por tamaño).
4. Siempre decir: modelo de escenarios, no predicción; recupero tras default = precio implícito (caso base) y 40% (estrés); sin impuestos;
   no es asesoramiento financiero. El objetivo de Ivo es balancear riesgo y retorno: si no hay default, repagar caución cuesta rendimiento
   (B rinde más); si lo hay, repagar protege el patrimonio de Cocos. Mostrar ambos lados.
Camino previo a la elección: `--pre-path "0:795.7,5:900,9:1050,11:1100"` (volátil, pico 1.100 pb en sep-27); por defecto constante en 796 pb. El informe `--compara const.json` muestra el efecto. S3 se llama "Reestructuración / canje".
LIMITACIÓN: el estado inicial está fijo en 30-oct-2026; cuando pasen meses, regenerar con el estado actualizado (agregar `--estado`/`--inicio` al modelo).

## Formato del email (htmlBody, tablas simples, sin JS)
1. Titular: 2-3 líneas con lo más importante.
2. Notas: tabla resumen, riesgos, volumen, próximas fechas.
3. Curva AR: tabla de bonos (precio, var, TIR, paridad, volumen), pendiente/riesgo país, lectura.
4. Cartera Cocos: pesos, TIR/duration ponderada, concentración, antigüedad del dato.
4b. Dónde alocar futuros ahorros (Parte 5).
4c. Serie de apalancamiento (Parte 6): tabla de 12 semanas + link a la planilla.
4d. Proyección de largo plazo (Parte 7): real vs proyectado, riesgo-retorno, link a las gráficas.
5. Fuentes y calidad de datos (qué fue web vs conector, qué faltó).
Enviá con `mcp__Gmail__send_message`. Si el envío falla, creá un draft con `create_draft`.
Si es feriado en AR y US, mandá un mail corto avisando que no hay datos nuevos.

## Reglas
- Cálculo teórico, no es el statement; si no cierra con la cuenta de Ivo manda el statement.
- Nunca fabriques precios/TIRs. Declarar faltantes.
- No hagas órdenes en IBKR ni toques alertas/watchlists: solo lectura.
