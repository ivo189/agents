#!/usr/bin/env python3
"""Agente Zonaprop: listados -> prefiltro -> fichas del top -> ranking.
Uso:  python3 run.py [--headed] [--solo Pichincha,Núñez] [--html-dir DIR]   (DIR = HTML guardado a mano, sin red)"""
import argparse, csv, datetime as dt, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
import parse, rank

ROOT = Path(__file__).parent
OUT = ROOT / "out"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--solo", help="zonas separadas por coma")
    ap.add_argument("--html-dir", help="usar HTMLs locales <zona>.html / <zona>_<id>.html en vez de la red")
    a = ap.parse_args()
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    c = cfg["criterios"]
    busq = [b for b in cfg["busquedas"] if not a.solo or b["zona"] in a.solo.split(",")]
    OUT.mkdir(exist_ok=True)
    fecha = dt.date.today().isoformat()

    fetcher = None
    if not a.html_dir:
        from fetch import Fetcher, page_url
        fetcher = Fetcher(OUT / "cache" / fecha, OUT / "perfil", a.headed, tuple(cfg["pausa_seg"]))

    rows = {}
    try:
        for b in busq:
            if a.html_dir:
                f = Path(a.html_dir) / f"{b['zona']}.html"
                pages = [f.read_text(encoding="utf-8")] if f.exists() else []
            else:
                pages = []
                for n in range(1, cfg["paginas_max"] + 1):
                    html = fetcher.get(page_url(b["url"], n), '[data-qa^="posting"]')
                    items = parse.parse_listing_page(html)
                    if not items:
                        break
                    pages.append(html)
            n0 = len(rows)
            for html in pages:
                for r in parse.parse_listing_page(html):
                    r.update(ciudad=b["ciudad"], zona=b["zona"])
                    rows.setdefault(r["id"], r)
            print(f"{b['zona']}: +{len(rows) - n0} avisos", file=sys.stderr)

        cand = rank.prefilter(list(rows.values()), c)
        cand.sort(key=lambda r: r["usd_m2"])
        cand = cand[: c["top_detalle"] * 2]  # margen: la ficha puede descartar
        print(f"{len(rows)} avisos, {len(cand)} candidatos tras prefiltro", file=sys.stderr)

        for r in cand[: c["top_detalle"] * 2]:
            try:
                if a.html_dir:
                    f = Path(a.html_dir) / f"{r['zona']}_{r['id']}.html"
                    html = f.read_text(encoding="utf-8") if f.exists() else ""
                else:
                    html = fetcher.get(r["url"])
                if html:
                    r.update(parse.parse_detail(html))
            except Exception as e:  # una ficha rota no frena el run
                print(f"ficha {r['id']}: {e}", file=sys.stderr)
    finally:
        if fetcher:
            fetcher.close()

    final = rank.finalize(cand, c)
    seen_f = OUT / "vistos.json"
    vistos = set(json.loads(seen_f.read_text())) if seen_f.exists() else set()
    nuevos = {r["id"] for r in final if r["id"] not in vistos}
    seen_f.write_text(json.dumps(sorted(vistos | {r["id"] for r in final})))

    (OUT / f"ranking_{fecha}.md").write_text(rank.to_markdown(final, c["top_reporte"], fecha, nuevos), encoding="utf-8")
    cols = ["id", "ciudad", "zona", "direccion", "precio", "m2_total", "m2_cub", "usd_m2", "mediana_ref",
            "descuento_pct", "score", "ambientes", "cocheras_final", "antiguedad", "expensas_txt", "flags", "url"]
    with open(OUT / f"ranking_{fecha}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for r in final:
            w.writerow({**r, "flags": " | ".join(r["flags"])})
    print((OUT / f"ranking_{fecha}.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
