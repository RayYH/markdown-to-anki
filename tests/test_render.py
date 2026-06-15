from markdown_to_anki.services.render import (
    extract_card_tags,
    markdown_metadata,
    markdown_to_html,
    split_multi_parts,
)

# ---------------------------------------------------------------------------
# split_multi_parts
# ---------------------------------------------------------------------------

SINGLE_CARD = """\
---
deck: Test
model: m2a-basic
---

<!--CARD-->

### Front

<!--FIELD-->

Back content
"""

MULTI_CARD = """\
---
deck: Test
model: m2a-basic
---

<!--CARD-->

### Card one

<!--FIELD-->

Answer one

<!--CARD-->

### Card two

<!--FIELD-->

Answer two
"""

CARD_WITH_TAGS = """\
---
deck: Test
---

<!--CARD-->
<!--TAGS: math, hard-->

### Question

<!--FIELD-->

Answer
"""


def test_split_single_card():
    parts = split_multi_parts(SINGLE_CARD)
    assert len(parts) == 1
    card_tags, fields = parts[0]
    assert card_tags == []
    assert len(fields) == 2


def test_split_multiple_cards():
    parts = split_multi_parts(MULTI_CARD)
    assert len(parts) == 2


def test_split_multiple_cards_fields():
    parts = split_multi_parts(MULTI_CARD)
    _, fields0 = parts[0]
    assert "Card one" in fields0[0]
    assert "Answer one" in fields0[1]


def test_split_card_tags_extracted():
    parts = split_multi_parts(CARD_WITH_TAGS)
    assert len(parts) == 1
    card_tags, fields = parts[0]
    assert card_tags == ["math", "hard"]


def test_split_card_tags_removed_from_content():
    parts = split_multi_parts(CARD_WITH_TAGS)
    _, fields = parts[0]
    assert "TAGS" not in fields[0]


# ---------------------------------------------------------------------------
# extract_card_tags
# ---------------------------------------------------------------------------


def test_extract_card_tags_single():
    tags, cleaned = extract_card_tags("<!--TAGS: math-->")
    assert tags == ["math"]
    assert "TAGS" not in cleaned


def test_extract_card_tags_multiple():
    tags, _ = extract_card_tags("<!--TAGS: a, b, c-->")
    assert tags == ["a", "b", "c"]


def test_extract_card_tags_empty_directive():
    tags, _ = extract_card_tags("<!--TAGS-->")
    assert tags == []


def test_extract_card_tags_case_insensitive():
    tags, _ = extract_card_tags("<!--tags: x-->")
    assert tags == ["x"]


# ---------------------------------------------------------------------------
# markdown_metadata
# ---------------------------------------------------------------------------


def test_markdown_metadata_basic():
    content = "---\ndeck: My::Deck\nmodel: m2a-basic\n---\n"
    meta = markdown_metadata(content)
    assert meta["deck"] == ["My::Deck"]
    assert meta["model"] == ["m2a-basic"]


def test_markdown_metadata_comma_tags():
    content = "---\ntags: cpp, io\n---\n"
    meta = markdown_metadata(content)
    assert meta["tags"] == ["cpp", "io"]


def test_markdown_metadata_skip_flag():
    content = "---\nskip: 1\n---\n"
    meta = markdown_metadata(content)
    assert meta["skip"] == ["1"]


def test_markdown_metadata_empty():
    meta = markdown_metadata("no frontmatter here")
    assert meta == {}


# ---------------------------------------------------------------------------
# markdown_to_html
# ---------------------------------------------------------------------------


def test_markdown_to_html_basic():
    html = markdown_to_html("**bold** and _italic_")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_markdown_to_html_image_flattened(tmp_path):
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    (img_dir / "foo.png").touch()
    md_file = tmp_path / "note.md"
    html = markdown_to_html("![](./images/foo.png)", base_path=str(md_file))
    assert 'src="foo.png"' in html


def test_markdown_to_html_audio_sound_tag(tmp_path):
    audio_dir = tmp_path / "audios"
    audio_dir.mkdir()
    (audio_dir / "clip.mp3").touch()
    md_file = tmp_path / "note.md"
    html = markdown_to_html("![](./audios/clip.mp3)", base_path=str(md_file))
    assert "[sound:clip.mp3]" in html
    assert "<img" not in html


def test_markdown_to_html_math_inline():
    html = markdown_to_html("$x^2$")
    assert r"\(x^2\)" in html


def test_markdown_to_html_math_block():
    html = markdown_to_html("$$f'(c)=\\frac{a}{b}$$")
    assert r"\[" in html
    assert r"\]" in html


def test_markdown_to_html_external_image_unchanged():
    html = markdown_to_html("![](https://example.com/img.png)")
    assert "https://example.com/img.png" in html


def test_markdown_to_html_no_base_path_relative_src_kept():
    # Without a base_path, the img src is still resolved to basename
    html = markdown_to_html("![](./images/foo.png)")
    assert 'src="foo.png"' in html


def test_cloze_syntax_passes_through():
    html = markdown_to_html("The capital of {{c1::France}} is {{c2::Paris}}.")
    assert "{{c1::France}}" in html
    assert "{{c2::Paris}}" in html


def test_cloze_multi_deletion_passes_through():
    html = markdown_to_html("{{c1::Water}} boils at {{c2::100}}°C.")
    assert "{{c1::Water}}" in html
    assert "{{c2::100}}" in html
