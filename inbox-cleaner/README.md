# inbox-cleaner

Agente para limpiar Gmail: inventario por remitente, baja masiva y priorización. Todo es **dry-run** salvo que pases `--apply`. Nada se borra para siempre: "papelera" es la TRASH de Gmail (30 días para recuperar).

## Setup (una vez)

1. En [Google Cloud Console](https://console.cloud.google.com/) creá un proyecto, activá la **Gmail API** y creá credenciales **OAuth client ID → Desktop app**.
2. En la pantalla de consentimiento agregá tu mail como usuario de prueba.
3. Bajá el JSON como `inbox-cleaner/credentials.json` (está en `.gitignore`).
4. `pip install -r requirements.txt`

La primera ejecución abre el navegador para autorizar (permisos: modificar mails y filtros; no puede enviar mails).

## Uso

```bash
python cleaner.py inventory          # 1. escanea no leídos -> state/senders.csv
# 2. abrí state/senders.csv y corregí la columna "decision": keep | unsub | trash | review
python cleaner.py clean              # dry-run: cuántos mails iría a la papelera
python cleaner.py clean --apply      # manda a papelera + crea filtros para que no vuelvan
python cleaner.py unsubscribe --apply  # baja one-click (RFC 8058); el resto queda en state/unsub_report.csv
python cleaner.py prioritize --apply # etiquetas Prioridad/* + filtros + marca importantes
```

## Cómo decide

- **keep**: remitentes a los que alguna vez le escribiste, o que están en `config.json` (`keep` / `priority`).
- **unsub**: más del 60 % es Promociones y tiene `List-Unsubscribe`.
- **trash**: promo sin link de baja.
- **review**: no es promo (Novedades, bancos, etc.). `clean` **no los toca**: decidilos vos en el CSV.
- Nunca toca mails con estrella.

## Consejos

- Corré `inventory` de nuevo después de limpiar para ver lo que quedó.
- Ajustá `config.json` antes de `clean`: ahí definís qué es prioridad (bancos, impuestos, viajes).
- Las bajas por `mailto:` o con formulario no se pueden automatizar: aparecen como `manual` en el reporte, y el filtro de `clean` igual los manda a la papelera.
