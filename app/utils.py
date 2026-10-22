import os
import re
from urllib.parse import urlparse, parse_qs

from flask import url_for

_YT_ID = re.compile(r"[A-Za-z0-9_-]{6,20}")
_DRIVE = re.compile(r"https://drive\.google\.com/file/d/([\w-]+)")


def youtube_embed(url):
    """Converte um link comum do YouTube em URL de embed.

    Retorna None se o link não for do YouTube.
    """
    if not url:
        return None
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().replace("www.", "")
    video_id = None

    if host == "youtu.be":
        video_id = parsed.path.lstrip("/")
    elif host in ("youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith(("/embed/", "/shorts/")):
            partes = parsed.path.split("/")
            video_id = partes[2] if len(partes) > 2 else None

    if video_id and _YT_ID.fullmatch(video_id):
        return f"https://www.youtube-nocookie.com/embed/{video_id}"
    return None


def pdf_src(valor):
    """Devolve a URL para exibir um PDF em iframe.

    Aceita o nome de um arquivo em app/static/docs/ ou um link do Google Drive.
    Retorna None para qualquer outra coisa.
    """
    if not valor:
        return None
    valor = valor.strip()

    drive = _DRIVE.match(valor)
    if drive:
        return f"https://drive.google.com/file/d/{drive.group(1)}/preview"
    if valor.startswith(("http://", "https://")):
        return None

    nome = os.path.basename(valor.replace("\\", "/"))  # evita path traversal
    if nome.lower().endswith(".pdf"):
        return url_for("static", filename=f"docs/{nome}")
    return None
