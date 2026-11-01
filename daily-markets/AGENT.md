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
2. **Citi / HSBC US / HSBC MX**: estados de cuenta PDF en carpetas de Drive (ids en `fuentes.json`);
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
6. Fondos HSBC MX: valor en MXN, rendimiento de la semana si el estado lo trae, y convertir a USD; no
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

## Formato del email (htmlBody, tablas simples, sin JS)
1. Titular: 2-3 líneas con lo más importante.
2. Notas: tabla resumen, riesgos, volumen, próximas fechas.
3. Curva AR: tabla de bonos (precio, var, TIR, paridad, volumen), pendiente/riesgo país, lectura.
4. Cartera Cocos: pesos, TIR/duration ponderada, concentración, antigüedad del dato.
5. Fuentes y calidad de datos (qué fue web vs conector, qué faltó).
Enviá con `mcp__Gmail__send_message`. Si el envío falla, creá un draft con `create_draft`.
Si es feriado en AR y US, mandá un mail corto avisando que no hay datos nuevos.

## Reglas
- Cálculo teórico, no es el statement; si no cierra con la cuenta de Ivo manda el statement.
- Nunca fabriques precios/TIRs. Declarar faltantes.
- No hagas órdenes en IBKR ni toques alertas/watchlists: solo lectura.
