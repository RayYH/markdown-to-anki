import os
import re

from bs4 import BeautifulSoup
from markdown import markdown, Markdown

PARAGRAPH_SEPERATOR = r"<!--CARD-->"
FIELD_SEPERATOR = r"<!--FIELD-->"
CARD_TAGS_RE = re.compile(r"<!--\s*TAGS:\s*(.*?)-->", re.IGNORECASE)

AUDIO_EXTENSIONS = {".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac", ".opus"}

extension_configs = {
    "mdx_math": {"enable_dollar_delimiter": True},
    "codehilite": {"use_pygments": True},
}


def split_multi_parts(content: str):
    sections = content.split(PARAGRAPH_SEPERATOR)
    items = []
    for section in sections:
        if FIELD_SEPERATOR in section:
            card_tags, cleaned = extract_card_tags(section)
            items.append((card_tags, cleaned.split(FIELD_SEPERATOR)))
    return items


def extract_card_tags(section: str):
    tags = []
    for match in CARD_TAGS_RE.finditer(section):
        tags += [t.strip() for t in match.group(1).split(",") if t.strip()]
    cleaned = CARD_TAGS_RE.sub("", section)
    return tags, cleaned


def markdown_metadata(content: str):
    md = Markdown(extensions=["meta"])
    md.convert(content)
    meta = getattr(md, "Meta", {})
    result = {}
    for key in meta:
        items = meta[key]
        if not items:
            continue
        vals = []
        for item in items:
            vals += item.split(",")
        result[key] = [v.strip() for v in vals]
    return result


def markdown_to_html(content: str, base_path: str | None = None) -> str:
    html = (
        markdown(
            content,
            extensions=[
                "mdx_math",
                "toc",
                "fenced_code",
                "codehilite",
                "tables",
                "meta",
            ],
            extension_configs=extension_configs,
        )
        .replace('<script type="math/tex">', "<anki-mathjax>")
        .replace("</script>", "</anki-mathjax>")
        .replace(
            '<script type="math/tex; mode=display">',
            '<anki-mathjax block="true">',
        )
    )

    # inline math: \(formula\)
    html = re.sub(r"<anki-mathjax>([\s\S]+?)</anki-mathjax>", r"\(\1\)", html)
    # block math: \[formula\]
    html = re.sub(
        r"<anki-mathjax block=\"true\">([\s\S]+?)</anki-mathjax>",
        r"\[\1\]",
        html,
    )

    if "<img" in html:
        base_dir = os.path.dirname(base_path) if base_path else None
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img"):
            src = str(img.get("src") or "")
            if (
                not src
                or src.startswith("http://")
                or src.startswith("https://")
            ):
                continue
            if base_dir and not os.path.isabs(src):
                abs_src = os.path.normpath(os.path.join(base_dir, src))
            else:
                abs_src = src
            filename = os.path.basename(abs_src)
            if os.path.splitext(filename)[1].lower() in AUDIO_EXTENSIONS:
                img.replace_with(f"[sound:{filename}]")
            else:
                img["src"] = filename
        html = str(soup)

    return html


def code_to_html(source, language):
    content = f"```{language}\n{source}\n```"
    return markdown(content, extensions=["fenced_code"])
