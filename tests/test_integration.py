"""
Integration tests that connect to a live Anki instance via AnkiConnect.

Skipped automatically when AnkiConnect is unreachable at localhost:8765.
To run: open Anki with the AnkiConnect plugin active, then:

    uv run pytest tests/test_integration.py -v

Cards created by these tests persist in Anki under M2A::IntegrationTest:: decks
so you can inspect the results. Delete those decks manually when done.
"""

import json
import os
import tempfile
import urllib.request
import uuid

import pytest

import markdown_to_anki.services.anki as anki_svc
from markdown_to_anki.helpers.path import set_resources_dir
from markdown_to_anki.services.anki import (
    ensure_models,
    import_medias,
    import_notes,
)
from markdown_to_anki.services.anki_api import AnkiApi


# ---------------------------------------------------------------------------
# Availability check (runs once at collection time)
# ---------------------------------------------------------------------------


def _anki_available() -> bool:
    try:
        req = urllib.request.Request(
            "http://localhost:8765",
            json.dumps({"action": "version", "version": 6}).encode(),
        )
        urllib.request.urlopen(req, timeout=2)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _anki_available(),
    reason="AnkiConnect not reachable at localhost:8765 — open Anki to run these tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_resources():
    yield
    set_resources_dir(None)
    anki_svc._user_models_cache = None
    anki_svc._user_models_cache_dir = None


@pytest.fixture(scope="session", autouse=True)
def ensure_builtin_models():
    """Register built-in m2a models once per session before any test runs."""
    ensure_models()


@pytest.fixture
def anki():
    return AnkiApi()


@pytest.fixture
def test_deck(anki):
    """Unique deck per test. Cards persist in Anki so you can inspect them.
    Delete the M2A::IntegrationTest:: decks manually when you no longer need them."""
    name = f"M2A::IntegrationTest::{uuid.uuid4().hex[:8]}"
    anki.create_deck(deck=name)
    return name


@pytest.fixture
def uid():
    """Unique ID per test invocation — embedded in note content to prevent
    Anki duplicate errors across multiple test runs."""
    return uuid.uuid4().hex[:8]


def _note_id_from_sidecar(md_path) -> int:
    sidecar = md_path.with_suffix(".anki")
    return json.loads(sidecar.read_text())["1"]


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def test_connection(anki):
    version = anki.version()
    assert isinstance(version, int)
    assert version >= 6


# ---------------------------------------------------------------------------
# ensure_models
# ---------------------------------------------------------------------------


def test_ensure_models_registers_builtins(anki):
    ensure_models()
    names = anki.model_names()
    assert "m2a-basic" in names
    assert "m2a-cloze" in names
    assert "m2a-english" in names
    assert "m2a-basic-reverse" in names


def test_ensure_models_is_idempotent(anki):
    result = ensure_models()
    names = anki.model_names()
    assert "m2a-basic" in names
    assert result["created"] == 0 or result["updated"] >= 0


# ---------------------------------------------------------------------------
# import_notes
# ---------------------------------------------------------------------------


def test_import_notes_creates_card(tmp_path, test_deck, anki, uid):
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\n---\n\n"
        f"<!--CARD-->\n\n### Front {uid}\n\n<!--FIELD-->\n\nBack {uid}\n"
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 1
    assert result["notes updated"] == 0

    note_id = _note_id_from_sidecar(md)
    info = anki.notes_info([note_id])
    assert info[0]["modelName"] == "m2a-basic"


def test_import_notes_fields_stored(tmp_path, test_deck, anki, uid):
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\n---\n\n"
        f"<!--CARD-->\n\n### Front {uid}\n\n<!--FIELD-->\n\nBack {uid}\n"
    )
    import_notes(md_folder=str(tmp_path))

    note_id = _note_id_from_sidecar(md)
    info = anki.notes_info([note_id])[0]
    assert uid in info["fields"]["Front"]["value"]
    assert uid in info["fields"]["Back"]["value"]


def test_import_notes_sidecar_written(tmp_path, test_deck, uid):
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\n---\n\n"
        f"<!--CARD-->\n\n### Q {uid}\n\n<!--FIELD-->\n\nA {uid}\n"
    )
    import_notes(md_folder=str(tmp_path))
    sidecar = tmp_path / "note.anki"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text())
    assert "1" in data
    assert isinstance(data["1"], int)


def test_import_notes_updates_card(tmp_path, test_deck, anki, uid):
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\n---\n\n"
        f"<!--CARD-->\n\n### Q {uid}\n\n<!--FIELD-->\n\nOriginal answer\n"
    )
    import_notes(md_folder=str(tmp_path))
    note_id = _note_id_from_sidecar(md)

    # Overwrite with new content — fresh mtime passes TIME_RANGE check
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\n---\n\n"
        f"<!--CARD-->\n\n### Q {uid}\n\n<!--FIELD-->\n\nUpdated answer\n"
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes updated"] == 1
    assert result["notes created"] == 0

    info = anki.notes_info([note_id])[0]
    assert "Updated answer" in info["fields"]["Back"]["value"]


def test_import_notes_multi_card(tmp_path, test_deck, anki, uid):
    md = tmp_path / "two.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\n---\n\n"
        f"<!--CARD-->\n\n### Card one {uid}\n\n<!--FIELD-->\n\nAnswer one\n\n"
        f"<!--CARD-->\n\n### Card two {uid}\n\n<!--FIELD-->\n\nAnswer two\n"
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 2

    sidecar = json.loads((tmp_path / "two.anki").read_text())
    assert "1" in sidecar and "2" in sidecar


def test_import_notes_tags_applied(tmp_path, test_deck, anki, uid):
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\ntags: math, hard\n---\n\n"
        f"<!--CARD-->\n\n### Q {uid}\n\n<!--FIELD-->\n\nA {uid}\n"
    )
    import_notes(md_folder=str(tmp_path))

    note_id = _note_id_from_sidecar(md)
    tags = anki.note_tags(note_id)
    assert "math" in tags
    assert "hard" in tags


def test_import_notes_card_tags_merged(tmp_path, test_deck, anki, uid):
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\ntags: file-tag\n---\n\n"
        f"<!--CARD-->\n<!--TAGS: card-tag-->\n\n### Q {uid}\n\n<!--FIELD-->\n\nA {uid}\n"
    )
    import_notes(md_folder=str(tmp_path))

    note_id = _note_id_from_sidecar(md)
    tags = anki.note_tags(note_id)
    assert "file-tag" in tags
    assert "card-tag" in tags


def test_import_notes_deck_created(tmp_path, anki, uid):
    deck_name = f"M2A::IntegrationTest::AutoCreate::{uuid.uuid4().hex[:6]}"
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {deck_name}\nmodel: m2a-basic\n---\n\n"
        f"<!--CARD-->\n\n### Q {uid}\n\n<!--FIELD-->\n\nA {uid}\n"
    )
    try:
        import_notes(md_folder=str(tmp_path))
        assert deck_name in anki.deck_names()
    finally:
        anki.delete_decks(decks=[deck_name])


def test_import_notes_image_rendered(tmp_path, test_deck, anki, uid):
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    (img_dir / "test.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-basic\n---\n\n"
        f"<!--CARD-->\n\n### Q {uid}\n\n<!--FIELD-->\n\n![](./images/test.png)\n"
    )
    import_notes(md_folder=str(tmp_path))

    note_id = _note_id_from_sidecar(md)
    info = anki.notes_info([note_id])[0]
    assert 'src="test.png"' in info["fields"]["Back"]["value"]


# ---------------------------------------------------------------------------
# import_medias
# ---------------------------------------------------------------------------


def test_import_medias_uploads_image(tmp_path, anki):
    filename = f"m2a_test_{uuid.uuid4().hex[:8]}.png"
    (tmp_path / filename).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    result = import_medias(md_folder=str(tmp_path))
    assert result["media files created"] == 1

    data = anki.retrieve_media_file(filename)
    assert data  # base64-encoded content returned by AnkiConnect


def test_import_medias_uploads_audio(tmp_path, anki):
    filename = f"m2a_test_{uuid.uuid4().hex[:8]}.mp3"
    (tmp_path / filename).write_bytes(b"ID3" + b"\x00" * 32)
    result = import_medias(md_folder=str(tmp_path))
    assert result["media files created"] == 1
    assert anki.retrieve_media_file(filename)


# ---------------------------------------------------------------------------
# Cloze
# ---------------------------------------------------------------------------


def test_cloze_model_registered(anki):
    ensure_models()
    assert "m2a-cloze" in anki.model_names()


def test_import_notes_cloze_creates_card(tmp_path, test_deck, anki, uid):
    md = tmp_path / "cloze.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-cloze\n---\n\n"
        f"<!--CARD-->\n\n"
        f"The capital of {{{{c1::France}}}} is {{{{c2::Paris}}}} [{uid}].\n\n"
        "<!--FIELD-->\n\nEuropean geography.\n"
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 1

    note_id = _note_id_from_sidecar(md)
    info = anki.notes_info([note_id])[0]
    assert info["modelName"] == "m2a-cloze"
    assert "{{c1::France}}" in info["fields"]["Text"]["value"]
    assert "{{c2::Paris}}" in info["fields"]["Text"]["value"]
    assert "European geography" in info["fields"]["Extra"]["value"]


def test_import_notes_cloze_multi_deletion(tmp_path, test_deck, anki, uid):
    md = tmp_path / "multi.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: m2a-cloze\n---\n\n"
        f"<!--CARD-->\n\n"
        f"{{{{c1::Water}}}} boils at {{{{c2::100}}}}°C [{uid}].\n\n"
        "<!--FIELD-->\n\nChemistry.\n\n"
        f"<!--CARD-->\n\n"
        f"The {{{{c1::mitochondria}}}} is the powerhouse of the {{{{c2::cell}}}} [{uid}].\n\n"
        "<!--FIELD-->\n\nBiology.\n"
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 2


# ---------------------------------------------------------------------------
# Custom note types
# ---------------------------------------------------------------------------

# Use a fixed model name so the test is idempotent — AnkiConnect has no
# deleteModel action, so we reuse the same name across runs.
CUSTOM_MODEL_NAME = "m2a-integration-test-custom"


@pytest.fixture(scope="module")
def custom_model():
    """Register the custom test model once; yields (model_name, resources_dir)."""
    resources = tempfile.mkdtemp()
    models_dir = os.path.join(resources, "models")
    os.makedirs(models_dir)
    with open(os.path.join(models_dir, "custom.yaml"), "w") as f:
        f.write(
            f"name: {CUSTOM_MODEL_NAME}\n"
            "fields:\n  - Question\n  - Hint\n  - Answer\n"
            "templates:\n"
            "  - name: card\n"
            '    front: "<div>{{{{Question}}}}</div><hr>{{{{Hint}}}}"\n'
            '    back: "<div>{{{{Answer}}}}</div>"\n'
        )
    set_resources_dir(resources)
    anki_svc._user_models_cache = None
    anki_svc._user_models_cache_dir = None
    ensure_models()
    yield CUSTOM_MODEL_NAME, resources


@pytest.fixture
def with_custom_model(custom_model):
    """Re-apply the resources dir each test (autouse reset_resources tears it down)."""
    model_name, resources = custom_model
    set_resources_dir(resources)
    anki_svc._user_models_cache = None
    anki_svc._user_models_cache_dir = None
    return model_name


def test_custom_model_registered(anki, with_custom_model):
    assert with_custom_model in anki.model_names()


def test_custom_model_has_correct_fields(anki, with_custom_model):
    info = anki.model_info(with_custom_model)
    # fields_on_templates: {template: [[front_fields], [back_fields]]}
    all_fields = {
        f
        for field_lists in info["fields_on_templates"].values()
        for fields in field_lists
        for f in fields
    }
    assert "Question" in all_fields
    assert "Answer" in all_fields


def test_import_notes_with_custom_model(
    tmp_path, test_deck, anki, with_custom_model, uid
):
    md = tmp_path / "note.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: {with_custom_model}\n---\n\n"
        f"<!--CARD-->\n\n### What is 2 + 2? [{uid}]\n\n"
        "<!--FIELD-->\n\nThink carefully.\n\n"
        "<!--FIELD-->\n\n4\n"
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 1

    note_id = _note_id_from_sidecar(md)
    info = anki.notes_info([note_id])[0]
    assert info["modelName"] == with_custom_model
    assert "2 + 2" in info["fields"]["Question"]["value"]
    assert "4" in info["fields"]["Answer"]["value"]


def test_import_notes_custom_model_multi_card(
    tmp_path, test_deck, anki, with_custom_model, uid
):
    md = tmp_path / "multi.md"
    md.write_text(
        f"---\ndeck: {test_deck}\nmodel: {with_custom_model}\n---\n\n"
        f"<!--CARD-->\n\n### Q1 [{uid}]\n\n<!--FIELD-->\n\nHint1\n\n<!--FIELD-->\n\nA1\n\n"
        f"<!--CARD-->\n\n### Q2 [{uid}]\n\n<!--FIELD-->\n\nHint2\n\n<!--FIELD-->\n\nA2\n"
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 2
