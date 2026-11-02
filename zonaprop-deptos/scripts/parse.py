"""Parsing de Zonaprop (listados y fichas). Puro: recibe HTML, devuelve dicts. Sin red."""
import re
from bs4 import BeautifulSoup

BASE = "https://www.zonaprop.com.ar"


def _num(s):
    """'185.000' -> 185000 ; '1.250,5' -> 1250 (se descartan decimales)."""
    s = s.split(",")[0]
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def parse_price(text):
    """-> (monto, moneda) con moneda 'USD' | 'ARS' | None."""
    t = (text or "").replace("\xa0", " ")
    m = re.search(r"(USD|U\$S|U\$D|\$)\s*([\d\.,]+)", t)
    if not m:
        return None, None
    cur = "ARS" if m.group(1) == "$" else "USD"
    return _num(m.group(2)), cur


def parse_features(text):
    t = (text or "").replace("\xa0", " ").lower()

    def g(pat):
        m = re.search(pat, t)
        return int(m.group(1)) if m else None

    return {
        "m2_total": g(r"(\d+)\s*m²\s*tot"),
        "m2_cub": g(r"(\d+)\s*m²\s*cub"),
        "ambientes": g(r"(\d+)\s*amb"),
        "dormitorios": g(r"(\d+)\s*dorm"),
        "banos": g(r"(\d+)\s*ba[ñn]"),
        "cocheras": g(r"(\d+)\s*coch"),
    }


def _txt(card, qa):
    el = card.select_one(f'[data-qa="{qa}"]')
    return el.get_text(" ", strip=True) if el else ""


def parse_listing_page(html):
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for card in soup.select("[data-to-posting], [data-posting-type]"):
        href = card.get("data-to-posting") or ""
        if not href:
            a = card.find("a", href=re.compile(r"/propiedades/"))
            href = a["href"] if a else ""
        pid = card.get("data-id") or (re.search(r"-(\d{6,})\.html", href) or [None, None])[1]
        if not pid or pid in seen:
            continue
        seen.add(pid)
        price, cur = parse_price(_txt(card, "POSTING_CARD_PRICE"))
        feats_txt = _txt(card, "POSTING_CARD_FEATURES") or card.get_text(" ", strip=True)
        desc = _txt(card, "POSTING_CARD_DESCRIPTION")
        exp_txt = _txt(card, "expensas")
        exp, exp_cur = parse_price(exp_txt)
        rec = {
            "id": str(pid),
            "url": href if href.startswith("http") else BASE + href,
            "precio": price,
            "moneda": cur,
            "expensas": exp,
            "expensas_moneda": exp_cur,
            "direccion": _txt(card, "POSTING_CARD_LOCATION"),
            "descripcion": desc,
        }
        rec.update(parse_features(feats_txt))
        out.append(rec)
    return out


def parse_detail(html):
    """Ficha: antigüedad (años; 0 = a estrenar), cocheras y señales de cochera opcional."""
    soup = BeautifulSoup(html, "lxml")
    t = soup.get_text(" ", strip=True).replace("\xa0", " ")
    tl = t.lower()
    ant = None
    m = re.search(r"antig[üu]edad\s*:?\s*(\d+)\s*años?", tl) or re.search(r"(\d+)\s*años?\s*de\s*antig", tl)
    if m:
        ant = int(m.group(1))
    elif re.search(r"a estrenar|antig[üu]edad\s*:?\s*a estrenar", tl):
        ant = 0
    elif re.search(r"en construcci[oó]n|en pozo", tl):
        ant = 0
    coch = None
    m = re.search(r"cocheras?\s*:?\s*(\d+)", tl) or re.search(r"(\d+)\s*cocheras?", tl)
    if m:
        coch = int(m.group(1))
    opcional = bool(re.search(
        r"cochera\s+(opcional|aparte|a parte|no incluida|a consultar)|(opcional|aparte|a parte)\s+cochera|"
        r"precio\s+(no\s+)?incluye\s+cochera", tl))
    return {"antiguedad": ant, "cocheras_detalle": coch, "cochera_opcional": opcional}
