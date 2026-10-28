"""Inspección estática reproducible de la aplicación mensual oficial ODEPA.

Descarga HTML y scripts JavaScript del mismo origen y registra posibles rutas
de API que aparecen literalmente en ellos. No invoca APIs candidatas, evalúa
JavaScript, infiere IDs ni produce precios. Ejecutar desde la raíz del repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from materias_primas_chile.prices import fetch
from materias_primas_chile.storage import atomic_write, receipt, write_json

DEFAULT_URL = "https://aplicativos.odepa.gob.cl/series-precios/series-tiempo"


class ScriptLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.base_href = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "base" and attrs.get("href"):
            self.base_href = attrs["href"]
        if tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])


def save_download(url: str, root: Path, suffix: str) -> tuple[Path, str]:
    payload = fetch(url)
    digest = hashlib.sha256(payload).hexdigest()
    path = root / f"{digest}{suffix}"
    atomic_write(path, payload)
    receipt(path, url=url, source="ODEPA monthly application static research",
            content_role="application_source_not_price_data")
    return path, payload.decode("utf-8", errors="replace")


def literals(text: str):
    # Literal strings only. Template strings with interpolations are recorded as
    # expressions for human inspection and are never transformed into endpoints.
    for match in re.finditer(r'''(["'`])((?:\\.|(?!\1)[^\\\n]){1,1800}?)\1''', text):
        yield match.start(), match.group(2)


def candidates(text: str, source_url: str):
    results = []
    keywords = re.compile(r"api|series|precio|producto|subsector|consulta|reporte|download|export|ipc|moneda|periodo", re.I)
    for position, literal in literals(text):
        if not keywords.search(literal):
            continue
        if not (literal.startswith(("https://", "http://", "/", "./", "../")) or "/" in literal):
            continue
        if any(character in literal for character in ("<", ">", "\n")):
            continue
        results.append({"literal": literal, "source_url": source_url,
                        "offset": position,
                        "context": text[max(0, position - 100):position + len(literal) + 120],
                        "contains_template_expression": "${" in literal,
                        "status": "unverified_literal_not_called"})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", default="data/raw/research/odepa_monthly")
    parser.add_argument("--max-scripts", type=int, default=40)
    args = parser.parse_args()
    if not 1 <= args.max_scripts <= 100:
        parser.error("--max-scripts debe estar entre1 y100")
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    html_path, html = save_download(args.url, root, ".html")
    links = ScriptLinks()
    links.feed(html)
    base = urljoin(args.url, links.base_href) if links.base_href else args.url
    origin = urlparse(args.url).netloc
    queue = deque((urljoin(base, script), "html_script_src") for script in links.scripts)
    visited, files, failures = set(), [], []
    found = candidates(html, args.url)
    while queue and len(visited) < args.max_scripts:
        url, discovery = queue.popleft()
        url = urldefrag(url)[0]
        if url in visited:
            continue
        if urlparse(url).scheme != "https" or urlparse(url).netloc != origin:
            failures.append({"url": url, "status": "skipped_external_origin_or_non_https"})
            continue
        visited.add(url)
        try:
            path, javascript = save_download(url, root, ".js")
        except Exception as exc:
            failures.append({"url": url, "status": "download_failed", "error": str(exc)})
            continue
        files.append({"url": url, "path": str(path), "discovery": discovery})
        found.extend(candidates(javascript, url))
        # Follow literal ES-module imports and named JS files only. Runtime
        # chunk-name expressions cannot establish a downloadable URL.
        for _, literal in literals(javascript):
            if re.fullmatch(r"(?:\.{0,2}/)?[A-Za-z0-9_./-]+\.js(?:\?[A-Za-z0-9=&_.-]+)?", literal):
                queue.append((urljoin(url, literal), "literal_js_reference"))
    unique = {(item["source_url"], item["literal"]): item for item in found}
    report = {"application_url": args.url, "html_path": str(html_path),
              "script_files": files, "failures": failures,
              "remaining_script_queue": len(queue), "max_scripts": args.max_scripts,
              "candidates": list(unique.values()),
              "interpretation": "Static strings only; no API endpoint, data schema or prices verified."}
    write_json(root / "discovery.json", report)
    print(json.dumps({"html": str(html_path), "scripts_downloaded": len(files),
                      "candidate_literals": len(unique), "failures": len(failures),
                      "report": str(root / "discovery.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
