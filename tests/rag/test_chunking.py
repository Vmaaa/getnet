from app.rag.chunking import detect_lang, split_markdown

FIXTURE_MD = """# Getnet Maquininhas

Intro paragraph about machines.

## Get Clássica

The Get Clássica works with magnetic stripe, chip and contactless. {filler}

## Get Smart

The Get Smart has touchscreen and apps. {filler}

### Rates

Rates depend on the plan. {filler}
"""


def _filler(words: int) -> str:
    return " ".join(f"palavra{i}conteudo" for i in range(words))


def _fixture() -> str:
    md = FIXTURE_MD
    return md.format(filler=_filler(120))


def test_detect_lang():
    assert detect_lang("https://www.getnet.net/en/our-solutions/omnichannel") == "en"
    assert detect_lang("https://site.getnet.com.br/pix") == "pt-BR"


def test_split_produces_breadcrumbs():
    chunks = split_markdown(_fixture(), "https://site.getnet.com.br/todas-as-maquininhas/")
    crumbs = {c.breadcrumbs for c in chunks}
    assert "Getnet Maquininhas > Get Clássica" in crumbs
    assert "Getnet Maquininhas > Get Smart > Rates" in crumbs


def test_chunk_size_cap():
    chunks = split_markdown(_fixture(), "https://site.getnet.com.br/pix")
    assert chunks
    for c in chunks:
        assert len(c.text) <= 1000


def test_consecutive_chunks_overlap():
    chunks = split_markdown(_fixture(), "https://site.getnet.com.br/pix")
    pairs = [
        (chunks[i - 1], chunks[i])
        for i in range(1, len(chunks))
        if chunks[i].breadcrumbs == chunks[i - 1].breadcrumbs
    ]
    assert pairs
    for prev, cur in pairs:
        tail = prev.text[-135:].strip()
        assert tail[:50] in cur.text


def test_chunk_index_sequential():
    chunks = split_markdown(_fixture(), "https://site.getnet.com.br/pix")
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_title_taken_from_h1():
    chunks = split_markdown(_fixture(), "https://site.getnet.com.br/pix")
    assert all(c.title == "Getnet Maquininhas" for c in chunks)


def test_oversized_paragraph_hard_split():
    md = "# Doc\n\n" + _filler(300)
    chunks = split_markdown(md, "https://site.getnet.com.br/pix")
    assert len(chunks) > 1
    assert all(len(c.text) <= 1000 for c in chunks)
