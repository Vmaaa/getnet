import re
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")


@dataclass
class Chunk:
    text: str
    url: str
    title: str
    lang: str
    breadcrumbs: str
    chunk_index: int


def detect_lang(url: str) -> str:
    return "en" if "/en/" in url else "pt-BR"


def _sections(md: str) -> tuple[str, list[tuple[str, str]]]:
    stack: list[str] = []
    title = ""
    current: list[str] = []
    sections: list[tuple[str, str]] = []
    for line in md.splitlines():
        match = HEADING_RE.match(line.strip())
        if match:
            if current:
                sections.append((" > ".join(stack), "\n".join(current).strip()))
                current = []
            depth = len(match.group(1))
            heading = match.group(2).strip()
            stack = stack[: depth - 1] + [heading]
            if not title:
                title = heading
        else:
            current.append(line)
    if current:
        sections.append((" > ".join(stack), "\n".join(current).strip()))
    return title, sections


def _hard_split(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    step = max_chars - overlap_chars
    pieces = []
    start = 0
    while start < len(text):
        pieces.append(text[start : start + max_chars])
        if start + max_chars >= len(text):
            break
        start += step
    return pieces


def _split_body(body: str, max_chars: int, overlap_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    pieces: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(para) > max_chars:
            if buf:
                pieces.append(buf)
                buf = ""
            pieces.extend(_hard_split(para, max_chars, overlap_chars))
            continue
        if buf and len(buf) + len(para) + 2 > max_chars:
            pieces.append(buf)
            tail = buf[-overlap_chars:] if overlap_chars else ""
            buf = f"{tail}\n\n{para}" if tail else para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        pieces.append(buf)
    return pieces


def split_markdown(
    md: str,
    url: str,
    max_chars: int = 900,
    overlap_chars: int = 135,
) -> list[Chunk]:
    title, sections = _sections(md)
    lang = detect_lang(url)
    chunks: list[Chunk] = []
    for crumbs, body in sections:
        if not body:
            continue
        header = crumbs or title
        for piece in _split_body(body, max_chars, overlap_chars):
            text = f"{header}\n\n{piece}" if header else piece
            chunks.append(
                Chunk(
                    text=text,
                    url=url,
                    title=title or url,
                    lang=lang,
                    breadcrumbs=crumbs,
                    chunk_index=len(chunks),
                )
            )
    return chunks
