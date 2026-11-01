# daily-markets
Agente programado (Claude Code scheduled task) lun-vie 8:30 ART. Spec en `AGENT.md`.
- `scripts/volume_projection.py`: proyección de volumen (mediana 20d + EWMA).
- `scripts/curve_math.py`: pendiente, tramos y butterfly de la curva.
Depende del skill `estado-notas-estructuradas` y de los conectores TradingView, IBKR y Gmail.
