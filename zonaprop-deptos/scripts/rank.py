"""Filtra, calcula USD/m², compara contra la mediana de la zona y rankea."""
import statistics as st


def usd_m2(r):
    base = r.get("m2_total") or r.get("m2_cub")
    if r.get("moneda") == "USD" and r.get("precio") and base:
        return r["precio"] / base
    return None


def prefilter(rows, c):
    """Antes de bajar fichas: USD, >=ambientes, m² razonables, USD/m² plausible.
    Cochera: si la tarjeta no la menciona se deja pasar (la ficha lo confirma)."""
    keep = []
    for r in rows:
        v = usd_m2(r)
        if v is None or not (c["usd_m2_min"] <= v <= c["usd_m2_max"]):
            continue
        if (r.get("m2_total") or r.get("m2_cub") or 0) < c["m2_min"]:
            continue
        if r.get("ambientes") is not None and r["ambientes"] < c["ambientes_min"]:
            continue
        if r.get("cocheras") is not None and r["cocheras"] < c["cochera_min"]:
            continue
        r["usd_m2"] = round(v)
        keep.append(r)
    return keep


def benchmarks(rows, c):
    by_zone, by_city = {}, {}
    for r in rows:
        by_zone.setdefault((r["ciudad"], r["zona"]), []).append(r["usd_m2"])
        by_city.setdefault(r["ciudad"], []).append(r["usd_m2"])
    def med(xs): return st.median(xs)
    out = {}
    for r in rows:
        z = by_zone[(r["ciudad"], r["zona"])]
        if len(z) >= c["min_grupo_benchmark"]:
            out[r["id"]] = (med(z), f"zona {r['zona']} (n={len(z)})")
        else:
            ci = by_city[r["ciudad"]]
            out[r["id"]] = (med(ci), f"ciudad {r['ciudad']} (n={len(ci)})")
    return out


def finalize(rows, c):
    """rows con datos de ficha ya mezclados. Aplica reglas duras y score."""
    res = []
    bm = benchmarks(rows, c)
    for r in rows:
        coch = r.get("cocheras_detalle") if r.get("cocheras_detalle") is not None else r.get("cocheras")
        if not coch or coch < c["cochera_min"]:
            continue
        if r.get("ambientes") is not None and r["ambientes"] < c["ambientes_min"]:
            continue
        flags = []
        if r.get("cochera_opcional"):
            flags.append("cochera opcional/aparte: el precio puede no incluirla")
        med, ref = bm[r["id"]]
        desc = (med - r["usd_m2"]) / med * 100
        score = desc
        ant = r.get("antiguedad")
        if ant is None:
            score -= c["penalizacion_antiguedad_desconocida"]; flags.append("antigüedad desconocida")
        elif ant > c["antiguedad_preferida_max"]:
            score -= c["penalizacion_antiguedad_mayor"]; flags.append(f"antigüedad {ant} años (> {c['antiguedad_preferida_max']})")
        if desc > 35:
            flags.append("descuento >35%: revisar que no sea error de publicación o m² inflados")
        if r.get("expensas") and r.get("expensas_moneda") == "ARS":
            r["expensas_txt"] = f"ARS {r['expensas']:,}".replace(",", ".")
        elif r.get("expensas"):
            r["expensas_txt"] = f"{r['expensas_moneda']} {r['expensas']:,}".replace(",", ".")
        r.update({"cocheras_final": coch, "mediana_ref": round(med), "ref": ref,
                  "descuento_pct": round(desc, 1), "score": round(score, 1), "flags": flags})
        res.append(r)
    res.sort(key=lambda x: x["score"], reverse=True)
    return res


def to_markdown(rows, top, fecha, nuevos=()):
    L = [f"# Departamentos 3+ amb con cochera – ranking por USD/m² ({fecha})", "",
         "Score = descuento % de USD/m² vs la mediana de su zona (con ajuste por antigüedad). "
         "Es un filtro de oportunidades, no una tasación: verificar m², estado y cochera antes de contactar.", "",
         "| # | Zona | USD | m² (tot/cub) | USD/m² | vs mediana | Amb | Coch | Antig. | Expensas | Notas | Link |",
         "|---|------|-----|--------------|--------|-----------|-----|------|--------|----------|-------|------|"]
    for i, r in enumerate(rows[:top], 1):
        ant = "?" if r.get("antiguedad") is None else ("estrenar" if r["antiguedad"] == 0 else f"{r['antiguedad']}a")
        nota = ("NUEVO; " if r["id"] in nuevos else "") + "; ".join(r["flags"])
        L.append(f"| {i} | {r['zona']} | {r['precio']:,} | {r.get('m2_total') or '-'}/{r.get('m2_cub') or '-'} | "
                 f"{r['usd_m2']:,} | {r['descuento_pct']:+.0f}% (med {r['mediana_ref']:,}) | {r.get('ambientes') or '-'} | "
                 f"{r['cocheras_final']} | {ant} | {r.get('expensas_txt','-')} | {nota} | [ver]({r['url']}) |".replace(",", "."))
    return "\n".join(L) + "\n"
