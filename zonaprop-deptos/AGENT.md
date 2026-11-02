# Agente: oportunidades de departamentos en Zonaprop (USD/m²)

Objetivo: encontrar buenas oportunidades de compra de departamentos **3+ ambientes con cochera** en
Rosario (Pichincha, Puerto Norte, Zona Río) y CABA (Palermo y sub-barrios, Las Cañitas, Núñez),
medidas por **USD/m²** frente a la mediana de su zona. Antigüedad preferida < 30 años.
Español rioplatense, directo. No es tasación ni asesoramiento: es un filtro para decidir a quién contactar.

## Flujo
1. `python3 run.py --headed` (config en `config.json`). Corre en la máquina de Ivo, no en la nube.
2. Revisar stderr: avisos por zona. **Una zona con 0 avisos = URL o selector roto**; decirlo, no ignorarlo.
3. Leer `out/ranking_<fecha>.md`. Resumir top 10: zona, USD, m², USD/m², descuento vs mediana, antigüedad,
   expensas, link. Marcar los **NUEVOS** (no estaban en corridas previas, `out/vistos.json`).
4. Sospechar de lo demasiado bueno: descuento >35%, cochera "opcional/aparte", m² totales inflados por
   terraza/balcón, antigüedad desconocida. Reportar esos flags; no esconderlos.

## Reglas
- Solo precios en USD (los ARS se descartan). Expensas se reportan aparte (suelen estar en ARS).
- USD/m² = precio / m² totales (fallback cubiertos). Comparar siempre dentro de la misma zona (n ≥ 4; si no, ciudad).
- Rosario y CABA tienen niveles de precio distintos: comparar entre ciudades solo si Ivo lo pide.
- Antigüedad > 30 años: penaliza 10 pts; desconocida: 3 pts. Ficha del aviso es la fuente de antigüedad y cocheras.
- Ritmo: pausas de 3-7 s, caché por día, sin paralelizar. No evadir bloqueos más allá de resolver el captcha a mano.
- Si el sitio bloquea o cambia, decirlo; no inventar datos ni rellenar con memoria.
