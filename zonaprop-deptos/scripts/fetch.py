"""Descarga con Playwright. Zonaprop está detrás de Cloudflare: correr desde una IP residencial
(tu máquina), idealmente con --headed y un perfil persistente. Cachea el HTML por día."""
import hashlib, random, re, time
from pathlib import Path


def page_url(url, n):
    if n <= 1:
        return url
    return re.sub(r"\.html$", f"-pagina-{n}.html", url)


class Fetcher:
    def __init__(self, cache_dir, profile_dir, headed=False, pausa=(3, 7)):
        from playwright.sync_api import sync_playwright
        self.cache = Path(cache_dir); self.cache.mkdir(parents=True, exist_ok=True)
        self.pausa = pausa
        self._pw = sync_playwright().start()
        self.ctx = self._pw.chromium.launch_persistent_context(
            str(profile_dir), headless=not headed, locale="es-AR",
            viewport={"width": 1366, "height": 900})
        self.page = self.ctx.new_page()

    def get(self, url, ready_selector=None):
        f = self.cache / (hashlib.md5(url.encode()).hexdigest() + ".html")
        if f.exists():
            return f.read_text(encoding="utf-8")
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        for _ in range(15):  # espera a que pase el challenge de Cloudflare
            title = self.page.title().lower()
            if "un momento" not in title and "just a moment" not in title:
                break
            time.sleep(2)
        if ready_selector:
            try:
                self.page.wait_for_selector(ready_selector, timeout=15000)
            except Exception:
                pass
        html = self.page.content()
        if "captcha" in html.lower()[:5000] or "cf-chl" in html[:5000]:
            raise RuntimeError(f"Bloqueado por anti-bot en {url}. Probá --headed y resolvelo a mano.")
        f.write_text(html, encoding="utf-8")
        time.sleep(random.uniform(*self.pausa))
        return html

    def close(self):
        self.ctx.close(); self._pw.stop()
