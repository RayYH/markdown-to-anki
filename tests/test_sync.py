import json

import pytest

import markdown_to_anki.services.anki as anki_svc
from markdown_to_anki.helpers.path import set_resources_dir
from markdown_to_anki.services.anki import (
    ensure_models,
    import_medias,
    import_notes,
)


@pytest.fixture(autouse=True)
def reset_resources():
    yield
    set_resources_dir(None)
    anki_svc._user_models_cache = None
    anki_svc._user_models_cache_dir = None


@pytest.fixture
def mock_anki(mocker):
    mock = mocker.MagicMock()
    mock.deck_names.return_value = ["Test"]
    mock.add_note.return_value = 12345
    mock.notes_info.return_value = [{"id": 12345, "tags": []}]
    mock.note_tags.return_value = []
    mock.card_deck_name.return_value = "Test"
    mock.model_names.return_value = []
    mocker.patch("markdown_to_anki.services.anki.AnkiApi", return_value=mock)
    return mock


def _write_md(path, content):
    path.write_text(content)
    return path


BASIC_CARD = """\
---
deck: Test
model: m2a-basic
---

<!--CARD-->

### Front

<!--FIELD-->

Back
"""

TWO_CARD = """\
---
deck: Test
model: m2a-basic
---

<!--CARD-->

### Card 1

<!--FIELD-->

Answer 1

<!--CARD-->

### Card 2

<!--FIELD-->

Answer 2
"""

# ---------------------------------------------------------------------------
# import_notes
# ---------------------------------------------------------------------------


def test_import_notes_creates_card(tmp_path, mock_anki):
    _write_md(tmp_path / "note.md", BASIC_CARD)
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 1
    assert result["notes updated"] == 0
    mock_anki.add_note.assert_called_once()


def test_import_notes_sidecar_written(tmp_path, mock_anki):
    _write_md(tmp_path / "note.md", BASIC_CARD)
    import_notes(md_folder=str(tmp_path))
    sidecar = tmp_path / "note.anki"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text())
    assert data["1"] == 12345


def test_import_notes_correct_fields(tmp_path, mock_anki):
    _write_md(tmp_path / "note.md", BASIC_CARD)
    import_notes(md_folder=str(tmp_path))
    call_kwargs = mock_anki.add_note.call_args.kwargs
    assert "Front" in call_kwargs["fields"]
    assert "Back" in call_kwargs["fields"]
    assert "Front" in call_kwargs["fields"]["Front"]
    assert "Back" in call_kwargs["fields"]["Back"]


def test_import_notes_multi_card_file(tmp_path, mock_anki):
    _write_md(tmp_path / "two.md", TWO_CARD)
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 2
    assert mock_anki.add_note.call_count == 2


def test_import_notes_updates_existing(tmp_path, mock_anki):
    _write_md(tmp_path / "note.md", BASIC_CARD)
    (tmp_path / "note.anki").write_text(json.dumps({"1": 99999}))
    mock_anki.notes_info.return_value = [{"id": 99999}]
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes updated"] == 1
    mock_anki.update_note_fields.assert_called_once()
    mock_anki.add_note.assert_not_called()


def test_import_notes_skips_old_file(tmp_path, mock_anki, mocker):
    _write_md(tmp_path / "old.md", BASIC_CARD)
    mocker.patch(
        "markdown_to_anki.services.anki.last_modified_time", return_value=0.0
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 0
    mock_anki.add_note.assert_not_called()


def test_import_notes_skip_metadata(tmp_path, mock_anki):
    _write_md(
        tmp_path / "skip.md",
        "---\nskip: 1\ndeck: Test\nmodel: m2a-basic\n---\n\n<!--CARD-->\n\n### Q\n\n<!--FIELD-->\n\nA\n",
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 0
    mock_anki.add_note.assert_not_called()


def test_import_notes_file_tags(tmp_path, mock_anki):
    _write_md(
        tmp_path / "note.md",
        "---\ndeck: Test\nmodel: m2a-basic\ntags: cpp, io\n---\n\n<!--CARD-->\n\n### Q\n\n<!--FIELD-->\n\nA\n",
    )
    import_notes(md_folder=str(tmp_path))
    tags = mock_anki.add_note.call_args.kwargs["tags"]
    assert "cpp" in tags
    assert "io" in tags


def test_import_notes_card_tags_merged(tmp_path, mock_anki):
    _write_md(
        tmp_path / "note.md",
        "---\ndeck: Test\nmodel: m2a-basic\ntags: cpp\n---\n\n<!--CARD-->\n<!--TAGS: hard-->\n\n### Q\n\n<!--FIELD-->\n\nA\n",
    )
    import_notes(md_folder=str(tmp_path))
    tags = mock_anki.add_note.call_args.kwargs["tags"]
    assert "cpp" in tags
    assert "hard" in tags


def test_import_notes_creates_deck(tmp_path, mock_anki):
    mock_anki.deck_names.return_value = []
    _write_md(
        tmp_path / "note.md",
        "---\ndeck: New::Deck\nmodel: m2a-basic\n---\n\n<!--CARD-->\n\n### Q\n\n<!--FIELD-->\n\nA\n",
    )
    import_notes(md_folder=str(tmp_path))
    mock_anki.create_deck.assert_called_once_with(deck="New::Deck")


def test_import_notes_walks_subdirectories(tmp_path, mock_anki):
    sub = tmp_path / "sub"
    sub.mkdir()
    _write_md(sub / "note.md", BASIC_CARD)
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 1


# ---------------------------------------------------------------------------
# import_medias
# ---------------------------------------------------------------------------


def test_import_medias_syncs_image(tmp_path, mock_anki):
    (tmp_path / "img.png").write_bytes(b"\x89PNG")
    result = import_medias(md_folder=str(tmp_path))
    assert result["media files created"] == 1
    mock_anki.store_media_file_from_path.assert_called_once()
    call_kwargs = mock_anki.store_media_file_from_path.call_args.kwargs
    assert call_kwargs["filename"] == "img.png"


def test_import_medias_syncs_audio(tmp_path, mock_anki):
    (tmp_path / "clip.mp3").write_bytes(b"ID3")
    result = import_medias(md_folder=str(tmp_path))
    assert result["media files created"] == 1


def test_import_medias_skips_trash(tmp_path, mock_anki):
    trash = tmp_path / ".trash"
    trash.mkdir()
    (trash / "img.png").write_bytes(b"\x89PNG")
    result = import_medias(md_folder=str(tmp_path))
    assert result["media files created"] == 0
    mock_anki.store_media_file_from_path.assert_not_called()


def test_import_medias_ignores_non_media(tmp_path, mock_anki):
    (tmp_path / "note.md").write_text("hello")
    result = import_medias(md_folder=str(tmp_path))
    assert result["media files created"] == 0


# ---------------------------------------------------------------------------
# ensure_models
# ---------------------------------------------------------------------------


def test_ensure_models_creates_builtin(mock_anki):
    mock_anki.model_names.return_value = []
    result = ensure_models()
    assert (
        result["created"] == 4
    )  # m2a-basic, m2a-cloze, m2a-english, m2a-basic-reverse
    assert mock_anki.create_model.call_count == 4


def test_ensure_models_updates_existing(mock_anki):
    mock_anki.model_names.return_value = [
        "m2a-basic",
        "m2a-cloze",
        "m2a-english",
        "m2a-basic-reverse",
    ]
    result = ensure_models()
    assert result["updated"] == 4
    assert result["created"] == 0
    mock_anki.update_model_styling.assert_called()


def test_import_notes_cloze_model(tmp_path, mock_anki):
    md = tmp_path / "cloze.md"
    md.write_text(
        "---\ndeck: Test\nmodel: m2a-cloze\n---\n\n"
        "<!--CARD-->\n\n"
        "The capital of {{c1::France}} is {{c2::Paris}}.\n\n"
        "<!--FIELD-->\n\nExtra info.\n"
    )
    result = import_notes(md_folder=str(tmp_path))
    assert result["notes created"] == 1
    call_kwargs = mock_anki.add_note.call_args.kwargs
    assert call_kwargs["model_name"] == "m2a-cloze"
    assert "{{c1::France}}" in call_kwargs["fields"]["Text"]
    assert "{{c2::Paris}}" in call_kwargs["fields"]["Text"]
    assert "Extra info" in call_kwargs["fields"]["Extra"]


def test_ensure_models_includes_user_models(tmp_path, mock_anki):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "custom.yaml").write_text(
        "name: custom\nfields: [F]\ntemplates:\n  - name: c\n    front: x\n    back: y\n"
    )
    set_resources_dir(str(tmp_path))
    mock_anki.model_names.return_value = []
    result = ensure_models()
    assert result["created"] == 5  # 4 built-ins + 1 custom
    assert any(
        "custom" in str(call) for call in mock_anki.create_model.call_args_list
    )


def test_ensure_models_user_overrides_builtin(tmp_path, mock_anki):
    (tmp_path / "models").mkdir()
    # Override m2a-basic with a custom version
    (tmp_path / "models" / "override.yaml").write_text(
        "name: m2a-basic\nfields: [MyQ, MyA]\ntemplates:\n  - name: c\n    front: x\n    back: y\n"
    )
    set_resources_dir(str(tmp_path))
    mock_anki.model_names.return_value = []
    result = ensure_models()
    # Still 4 total (override replaces, doesn't add)
    assert result["created"] == 4
