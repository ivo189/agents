# zonaprop-deptos
Busca en Zonaprop deptos de 3+ ambientes con cochera en Rosario (Pichincha, Puerto Norte, Zona Río) y
CABA (Palermo y sub-barrios, Las Cañitas, Núñez) y los rankea por USD/m² contra la mediana de su zona.
Preferencia por antigüedad ≤ 30 años (penaliza, no excluye). Spec del agente en `AGENT.md`.

## Uso (en tu máquina; Zonaprop bloquea IPs de datacenter)
```bash
pip install -r requirements.txt && playwright install chromium
python3 run.py --headed                 # todo; resultados en out/ranking_<fecha>.md/.csv
python3 run.py --solo Pichincha,Núñez   # algunas zonas
python3 run.py --html-dir carpeta/      # sin red: <zona>.html y <zona>_<id>.html guardados a mano
```
Tests: `python3 -c "import sys; sys.path.insert(0,'tests'); import test_agent as t; [getattr(t,n)() for n in dir(t) if n.startswith('test_')]"`

## Pendiente de verificar contra el sitio real
Este código se armó sin acceso a Zonaprop (el sandbox lo bloqueaba), así que **nunca corrió contra el sitio**:
1. Las URLs de `config.json` son suposiciones: abrilas y corregilas (o pegá la URL ya filtrada).
2. Los selectores `data-qa` de `scripts/parse.py` pueden haber cambiado; si `run.py` imprime 0 avisos, ahí está.
3. Cloudflare puede pedir captcha: usá `--headed` y resolvelo una vez (el perfil queda en `out/perfil`).
