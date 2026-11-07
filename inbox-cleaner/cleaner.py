#!/usr/bin/env python3
"""Agente de limpieza de Gmail: inventario -> decisiones -> limpieza/baja -> prioridades.

Todo comando que modifica algo es DRY-RUN salvo que pases --apply.
Nada se borra para siempre: "papelera" = TRASH de Gmail (30 dias para recuperar).
"""
import argparse
import csv
import json
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]
HERE = Path(__file__).parent
STATE = HERE / "state"
STATE.mkdir(exist_ok=True)
CACHE = STATE / "inventory.json"
SENDERS_CSV = STATE / "senders.csv"
FILTERS_DONE = STATE / "filters_done.json"
VALID = {"keep", "unsub", "trash", "review"}
AUTOMATED = ("noreply", "no-reply", "donotreply", "do-not-reply", "mailer-daemon")


# ---------- infraestructura ----------
def service():
    tok = HERE / "token.json"
    creds = Credentials.from_authorized_user_file(str(tok), SCOPES) if tok.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(HERE / "credentials.json"), SCOPES)
            creds = flow.run_local_server(port=0)
        tok.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def execute(req, tries=6):
    for i in range(tries):
        try:
            return req.execute()
        except HttpError as e:
            if e.resp.status in (429, 500, 503) or (e.resp.status == 403 and "ate" in str(e)):
                time.sleep(2**i)
                continue
            raise
    raise RuntimeError("demasiados reintentos")


def load_cfg():
    return json.loads((HERE / "config.json").read_text())


def list_ids(svc, q):
    ids, tok = [], None
    while True:
        r = execute(svc.users().messages().list(userId="me", q=q, maxResults=500, pageToken=tok))
        ids += [m["id"] for m in r.get("messages", [])]
        tok = r.get("nextPageToken")
        if not tok:
            return ids


def fetch_meta(svc, ids, headers):
    out = {}

    def cb(_rid, resp, exc):
        if exc is None:
            out[resp["id"]] = resp

    for attempt in range(2):  # segundo pase para los que fallaron
        todo = [i for i in ids if i not in out]
        for i in range(0, len(todo), 50):
            b = svc.new_batch_http_request(callback=cb)
            for mid in todo[i : i + 50]:
                b.add(svc.users().messages().get(userId="me", id=mid, format="metadata", metadataHeaders=headers))
            for t in range(5):
                try:
                    b.execute()
                    break
                except HttpError:
                    time.sleep(2**t)
            print(f"\r  {min(i + 50, len(todo))}/{len(todo)}", end="", flush=True)
            time.sleep(0.2)
        print()
    return out


def hdr(msg, name):
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def batch_modify(svc, ids, add=(), remove=(), dry=True, what=""):
    print(f"  {what}: {len(ids)} mensajes" + (" (dry-run)" if dry else ""))
    if dry:
        return
    for i in range(0, len(ids), 1000):
        execute(svc.users().messages().batchModify(
            userId="me", body={"ids": ids[i : i + 1000], "addLabelIds": list(add), "removeLabelIds": list(remove)}))


def make_filters(svc, kind, emails, action, dry):
    done = set(json.loads(FILTERS_DONE.read_text())) if FILTERS_DONE.exists() else set()
    emails = sorted(e for e in emails if f"{kind}:{e}" not in done)
    n = (len(emails) + 39) // 40
    print(f"  filtros '{kind}': {len(emails)} remitentes en {n} filtros" + (" (dry-run)" if dry else ""))
    if dry:
        return
    for i in range(0, len(emails), 40):
        chunk = emails[i : i + 40]
        execute(svc.users().settings().filters().create(
            userId="me", body={"criteria": {"query": "from:(" + " OR ".join(chunk) + ")"}, "action": action}))
        done.update(f"{kind}:{e}" for e in chunk)
        FILTERS_DONE.write_text(json.dumps(sorted(done)))


# ---------- 1. inventario ----------
def cmd_inventory(args):
    svc = service()
    print("Listando no leidos...")
    ids = list_ids(svc, "is:unread")
    print(f"{len(ids)} mensajes sin leer. Leyendo cabeceras...")
    meta = fetch_meta(svc, ids, ["From", "List-Unsubscribe", "List-Unsubscribe-Post"])
    msgs = []
    for m in meta.values():
        name, email = parseaddr(hdr(m, "From"))
        msgs.append({
            "id": m["id"], "email": email.lower(), "name": name, "labels": m.get("labelIds", []),
            "date": int(m.get("internalDate", 0)), "unsub": hdr(m, "List-Unsubscribe"),
            "post": "one-click" in hdr(m, "List-Unsubscribe-Post").lower(),
        })
    print("Leyendo a quien le escribiste (contactos reales)...")
    sent = fetch_meta(svc, list_ids(svc, "in:sent"), ["To", "Cc"])
    contacts = set()
    for m in sent.values():
        for field in ("To", "Cc"):
            for part in hdr(m, field).split(","):
                e = parseaddr(part)[1].lower()
                if e:
                    contacts.add(e)
    CACHE.write_text(json.dumps({"messages": msgs, "contacts": sorted(contacts)}))
    write_senders_csv(msgs, contacts, load_cfg())


def protected_reason(email, cfg):
    if any(p.lower() in email for p in cfg["keep"]):
        return "config.keep"
    for rule in cfg["priority"]:
        if any(p.lower() in email for p in rule["from"]):
            return f"prioridad: {rule['label']}"
    return ""


def aggregate(msgs):
    agg = defaultdict(lambda: {"n": 0, "promo": 0, "last": 0, "name": "", "unsub": "", "post": False})
    for m in sorted(msgs, key=lambda x: x["date"]):
        a = agg[m["email"]]
        a["n"] += 1
        a["promo"] += "CATEGORY_PROMOTIONS" in m["labels"]
        a["last"], a["name"] = m["date"], m["name"] or a["name"]
        if m["unsub"]:
            a["unsub"], a["post"] = m["unsub"], m["post"]
    return agg


def suggest(email, a, cfg, contacts):
    if email in contacts:
        return "keep", "le escribiste alguna vez"
    why = protected_reason(email, cfg)
    if why:
        return "keep", why
    if a["promo"] / a["n"] >= 0.6:
        return ("unsub", "promo con baja") if a["unsub"] else ("trash", "promo sin link de baja")
    return "review", "no es promo: decidilo vos"


def write_senders_csv(msgs, contacts, cfg):
    agg = aggregate(msgs)
    rows = sorted(agg.items(), key=lambda kv: -kv[1]["n"])
    with SENDERS_CSV.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["email", "nombre", "sin_leer", "pct_promo", "ultimo", "tiene_baja", "one_click", "decision", "motivo"])
        for email, a in rows:
            d, why = suggest(email, a, cfg, contacts)
            last = datetime.fromtimestamp(a["last"] / 1000, timezone.utc).date()
            w.writerow([email, a["name"], a["n"], round(100 * a["promo"] / a["n"]), last,
                        "si" if a["unsub"] else "no", "si" if a["post"] else "no", d, why])
    print(f"\n{len(rows)} remitentes -> {SENDERS_CSV}")
    print("Revisa la columna 'decision' (keep | unsub | trash | review) y despues corre 'clean'.")


def read_decisions():
    out = {}
    with SENDERS_CSV.open() as f:
        for r in csv.DictReader(f):
            d = r["decision"].strip().lower()
            if d not in VALID:
                raise SystemExit(f"Decision invalida '{d}' para {r['email']} (usa {sorted(VALID)})")
            out[r["email"]] = d
    return out


# ---------- 2. limpieza + baja ----------
def cmd_clean(args):
    cache = json.loads(CACHE.read_text())
    dec = read_decisions()
    ids, filt = [], set()
    for m in cache["messages"]:
        if dec.get(m["email"]) in ("trash", "unsub") and "STARRED" not in m["labels"]:
            ids.append(m["id"])
            filt.add(m["email"])
    svc = service()
    batch_modify(svc, ids, add=["TRASH"], remove=["INBOX", "UNREAD"], dry=not args.apply, what="a la papelera")
    if args.filters:
        make_filters(svc, "trash", filt, {"addLabelIds": ["TRASH"], "removeLabelIds": ["INBOX"]}, not args.apply)
    keep = sum(1 for d in dec.values() if d == "keep")
    rev = sum(1 for d in dec.values() if d == "review")
    print(f"  intactos: {keep} remitentes 'keep', {rev} en 'review'")


def cmd_unsubscribe(args):
    cache = json.loads(CACHE.read_text())
    dec = read_decisions()
    latest = {}
    for m in cache["messages"]:
        if dec.get(m["email"]) == "unsub" and m["unsub"] and m["date"] >= latest.get(m["email"], {}).get("date", 0):
            latest[m["email"]] = m
    report = STATE / "unsub_report.csv"
    with report.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["email", "resultado", "manual"])
        for email, m in sorted(latest.items()):
            links = [x.strip(" <>") for x in m["unsub"].split(",")]
            https = next((x for x in links if x.startswith("https://")), "")
            if m["post"] and https:
                if args.apply:
                    try:
                        req = urllib.request.Request(https, data=b"List-Unsubscribe=One-Click", method="POST")
                        with urllib.request.urlopen(req, timeout=20) as r:
                            res = f"ok {r.status}"
                    except Exception as e:  # noqa: BLE001
                        res = f"fallo {e}"
                else:
                    res = "one-click (dry-run)"
                w.writerow([email, res, ""])
            else:
                w.writerow([email, "manual", " | ".join(links)])
    print(f"Reporte -> {report}. 'manual' = abri el link a mano (o el filtro de 'clean' ya los manda a papelera).")


# ---------- 3. prioridades ----------
def label_id(svc, name):
    for lb in execute(svc.users().labels().list(userId="me")).get("labels", []):
        if lb["name"] == name:
            return lb["id"]
    return execute(svc.users().labels().create(userId="me", body={"name": name}))["id"]


def cmd_prioritize(args):
    cfg, cache = load_cfg(), json.loads(CACHE.read_text()) if CACHE.exists() else {"contacts": []}
    people = sorted(e for e in cache["contacts"] if not any(a in e for a in AUTOMATED))
    rules = [(r["label"], r["from"]) for r in cfg["priority"]] + [("Prioridad/Personas", people)]
    svc = service()
    for label, senders in rules:
        if not senders:
            continue
        print(f"{label}: {len(senders)} remitentes/dominios")
        if args.apply:
            lid = label_id(svc, label)
            make_filters(svc, "prio:" + label, senders, {"addLabelIds": [lid, "IMPORTANT"]}, False)
            for i in range(0, len(senders), 40):
                q = "in:inbox from:(" + " OR ".join(senders[i : i + 40]) + ")"
                batch_modify(svc, list_ids(svc, q), add=[lid, "IMPORTANT"], dry=False, what="etiquetar existentes")
        else:
            print("  (dry-run: usa --apply para crear etiqueta + filtros y etiquetar lo existente)")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inventory", help="1. escanea no leidos y genera state/senders.csv")
    for name, fn in (("clean", cmd_clean), ("unsubscribe", cmd_unsubscribe), ("prioritize", cmd_prioritize)):
        s = sub.add_parser(name)
        s.add_argument("--apply", action="store_true", help="ejecutar de verdad (sin esto es dry-run)")
        if name == "clean":
            s.add_argument("--no-filters", dest="filters", action="store_false", help="no crear filtros para lo futuro")
        s.set_defaults(fn=fn)
    args = p.parse_args()
    (cmd_inventory if args.cmd == "inventory" else args.fn)(args)


if __name__ == "__main__":
    main()
