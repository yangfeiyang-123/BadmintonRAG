from __future__ import annotations

import re
from html import unescape
from pathlib import Path


def extract_html_text(path: Path) -> str:
    html = path.read_text(encoding="utf-8", errors="replace")
    html = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", html)
    html = re.sub(r"(?is)<(nav|footer|header).*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</(p|h1|h2|h3|li|tr)>", "\n", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()
