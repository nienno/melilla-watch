"""Detect changes to the Melilla 'Arquitecto/a' selection-process page and push via ntfy."""
import hashlib, html, os, re, sys, urllib.request
from pathlib import Path

URL = ("https://www.melilla.es/melillaportal/contenedor.jsp"
       "?seccion=s_fdes_d4_v1.jsp&contenido=32085&nivel=1400&tipo=6")
STATE = Path("state.txt")


def fetch() -> str:
    req = urllib.request.Request(URL, headers={"User-Agent": "melilla-watch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("latin-1")


def extract(page: str) -> str:
    """Return only the announcement list + 'Fecha de actualización' (ignores sidebar noise)."""
    page = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", "", page)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", page))
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    start = next(i for i, l in enumerate(lines) if l == "volver") + 1
    end = next(i for i, l in enumerate(lines) if l.startswith("Fecha de actualización")) + 1
    return "\n".join(lines[start:end])


def notify(title: str, body: str, priority: str = "high") -> None:
    topic = os.environ["NTFY_TOPIC"]
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}", data=body.encode(),
        headers={"Title": title.encode("utf-8").decode("latin-1"),
                 "Priority": priority, "Click": URL, "Tags": "rotating_light"})
    urllib.request.urlopen(req, timeout=30)


def main() -> int:
    try:
        current = extract(fetch())
    except Exception as e:  # page down or layout changed -> don't spam, just fail the run
        print(f"fetch/parse failed: {e}", file=sys.stderr)
        return 1
    old = STATE.read_text(encoding="utf-8") if STATE.exists() else None
    if current == old:
        print("no change")
        return 0
    STATE.write_text(current, encoding="utf-8")
    if old is None:
        print("baseline saved")
        notify("Melilla watch activo", "Monitorizando la página. Te avisaré de cambios.", "default")
        return 0
    new_lines = [l for l in current.splitlines() if l not in set(old.splitlines())]
    body = "\n".join(new_lines)[:3500] or "La página ha cambiado."
    print("CHANGED:\n" + body)
    notify("Melilla Arquitecto/a: página actualizada", body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
