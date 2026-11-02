import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import parse, rank

C = json.loads((Path(__file__).parent.parent / "config.json").read_text(encoding="utf-8"))["criterios"]


def card(pid, price, feats, loc="Av. Test 123, Palermo"):
    return f'''<div data-id="{pid}" data-posting-type="PROPERTY" data-to-posting="/propiedades/clasificado/veclapin-depto-{pid}.html">
      <div data-qa="POSTING_CARD_PRICE">{price}</div><div data-qa="expensas">$ 150.000 Expensas</div>
      <div data-qa="POSTING_CARD_LOCATION">{loc}</div>
      <div data-qa="POSTING_CARD_FEATURES"><span>{feats}</span></div></div>'''


def test_parse_price():
    assert parse.parse_price("USD 185.000") == (185000, "USD")
    assert parse.parse_price("$ 120.000.000") == (120000000, "ARS")


def test_parse_card():
    html = card("100000001", "USD 185.000", "120 m² tot. 100 m² cub. 4 amb. 3 dorm. 2 baños 1 coch.")
    (r,) = parse.parse_listing_page(html)
    assert (r["precio"], r["m2_total"], r["m2_cub"], r["ambientes"], r["cocheras"]) == (185000, 120, 100, 4, 1)
    assert r["expensas"] == 150000 and r["url"].endswith("depto-100000001.html")


def test_detail():
    d = parse.parse_detail("<p>Antigüedad 12 años</p><p>Cocheras 2</p>")
    assert d == {"antiguedad": 12, "cocheras_detalle": 2, "cochera_opcional": False}
    assert parse.parse_detail("<p>Edificio a estrenar. Cochera opcional.</p>")["antiguedad"] == 0
    assert parse.parse_detail("<p>Cochera opcional</p>")["cochera_opcional"] is True


def test_rank_and_filters():
    html = "".join([
        card(f"20000000{i}", f"USD {p}", "100 m² tot. 90 m² cub. 3 amb. 1 coch.")
        for i, p in enumerate([200000, 210000, 220000, 230000, 140000])
    ] + [
        card("300000001", "USD 90.000", "100 m² tot. 3 amb. 1 coch."),          # barato pero sin ficha limpia
        card("300000002", "USD 150.000", "100 m² tot. 2 amb. 1 coch."),         # 2 amb -> afuera
        card("300000003", "$ 90.000.000", "100 m² tot. 3 amb. 1 coch."),        # ARS -> afuera
        card("300000004", "USD 100.000", "100 m² tot. 3 amb."),                 # sin cochera en tarjeta, ficha decide
    ])
    rows = parse.parse_listing_page(html)
    for r in rows:
        r.update(ciudad="CABA", zona="Palermo")
    cand = rank.prefilter(rows, C)
    ids = {r["id"] for r in cand}
    assert "300000002" not in ids and "300000003" not in ids
    by = {r["id"]: r for r in cand}
    by["200000004"].update(antiguedad=40)                     # el más barato pero viejo
    by["300000004"].update(antiguedad=10, cocheras_detalle=0) # ficha: sin cochera -> afuera
    by["300000001"].update(antiguedad=5)
    final = rank.finalize(cand, C)
    out = [r["id"] for r in final]
    assert "300000004" not in out
    assert out[0] == "300000001"                              # mayor descuento, nuevo
    old = next(r for r in final if r["id"] == "200000004")
    assert any("antigüedad 40" in f for f in old["flags"])
    assert "| 1 |" in rank.to_markdown(final, 5, "2026-11-02")
