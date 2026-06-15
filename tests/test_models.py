import pytest

import markdown_to_anki.services.anki as anki_svc
from markdown_to_anki.helpers.path import set_resources_dir
from markdown_to_anki.services.anki import (
    _load_user_models,
    model_definition,
)


@pytest.fixture(autouse=True)
def reset_resources():
    """Reset resources dir and user model cache between tests."""
    yield
    set_resources_dir(None)
    anki_svc._user_models_cache = None
    anki_svc._user_models_cache_dir = None


# ---------------------------------------------------------------------------
# _load_user_models
# ---------------------------------------------------------------------------


def test_no_resources_dir():
    # No resources dir set → empty dict
    assert _load_user_models() == {}


def test_empty_models_dir(tmp_path):
    (tmp_path / "models").mkdir()
    set_resources_dir(str(tmp_path))
    assert _load_user_models() == {}


def test_model_inline_content(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "my-vocab.yaml").write_text(
        """
name: my-vocab
fields:
  - Word
  - Definition
css: ".card { color: red; }"
templates:
  - name: card
    front: "<div>{{Word}}</div>"
    back: "<div>{{Definition}}</div>"
"""
    )
    set_resources_dir(str(tmp_path))
    models = _load_user_models()

    assert "my-vocab" in models
    m = models["my-vocab"]
    assert m["modelName"] == "my-vocab"
    assert m["inOrderFields"] == ["Word", "Definition"]
    assert m["css"] == ".card { color: red; }"
    assert len(m["cardTemplates"]) == 1
    assert m["cardTemplates"][0]["Name"] == "card"
    assert m["cardTemplates"][0]["Front"] == "<div>{{Word}}</div>"
    assert m["cardTemplates"][0]["Back"] == "<div>{{Definition}}</div>"


def test_model_file_references(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "styles").mkdir()
    (tmp_path / "templates" / "my-model").mkdir(parents=True)

    (tmp_path / "styles" / "my-model.css").write_text(".card{}")
    (tmp_path / "templates" / "my-model" / "front.html").write_text(
        "<div>{{Q}}</div>"
    )
    (tmp_path / "templates" / "my-model" / "back.html").write_text(
        "<div>{{A}}</div>"
    )
    (tmp_path / "models" / "my-model.yaml").write_text(
        """
name: my-model
fields: [Q, A]
css_file: styles/my-model.css
templates:
  - name: qa
    front_file: templates/my-model/front.html
    back_file: templates/my-model/back.html
"""
    )
    set_resources_dir(str(tmp_path))
    m = _load_user_models()["my-model"]

    assert m["css"] == ".card{}"
    assert m["cardTemplates"][0]["Front"] == "<div>{{Q}}</div>"
    assert m["cardTemplates"][0]["Back"] == "<div>{{A}}</div>"


def test_model_skips_missing_name(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "bad.yaml").write_text("fields: [A, B]\n")
    set_resources_dir(str(tmp_path))
    assert _load_user_models() == {}


def test_model_skips_missing_fields(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "bad.yaml").write_text("name: bad-model\n")
    set_resources_dir(str(tmp_path))
    assert _load_user_models() == {}


def test_model_is_cloze_default_false(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "m.yaml").write_text(
        "name: m\nfields: [F]\ntemplates:\n  - name: c\n    front: x\n    back: y\n"
    )
    set_resources_dir(str(tmp_path))
    assert _load_user_models()["m"]["isCloze"] is False


def test_model_multi_template(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "m.yaml").write_text(
        """
name: m
fields: [F, B]
templates:
  - name: forward
    front: "{{F}}"
    back: "{{B}}"
  - name: reverse
    front: "{{B}}"
    back: "{{F}}"
"""
    )
    set_resources_dir(str(tmp_path))
    templates = _load_user_models()["m"]["cardTemplates"]
    assert len(templates) == 2
    assert templates[0]["Name"] == "forward"
    assert templates[1]["Name"] == "reverse"


# ---------------------------------------------------------------------------
# model_definition
# ---------------------------------------------------------------------------


def test_model_definition_builtin_m2a_basic():
    m = model_definition("m2a-basic")
    assert m is not None
    assert m["modelName"] == "m2a-basic"
    assert "Front" in m["inOrderFields"]
    assert "Back" in m["inOrderFields"]


def test_model_definition_builtin_m2a_english():
    m = model_definition("m2a-english")
    assert m is not None
    assert "Word" in m["inOrderFields"]


def test_model_definition_builtin_case_insensitive():
    assert model_definition("M2A-BASIC") is not None


def test_model_definition_unknown_returns_none():
    assert model_definition("does-not-exist") is None


def test_model_definition_user_found(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "custom.yaml").write_text(
        "name: custom\nfields: [X]\ntemplates:\n  - name: c\n    front: x\n    back: y\n"
    )
    set_resources_dir(str(tmp_path))
    m = model_definition("custom")
    assert m is not None
    assert m["modelName"] == "custom"


def test_model_definition_user_overrides_builtin(tmp_path):
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "override.yaml").write_text(
        "name: m2a-basic\nfields: [MyFront, MyBack]\ntemplates:\n  - name: c\n    front: x\n    back: y\n"
    )
    set_resources_dir(str(tmp_path))
    m = model_definition("m2a-basic")
    assert m["inOrderFields"] == ["MyFront", "MyBack"]


def test_cache_invalidates_on_dir_change(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    (dir_a / "models").mkdir(parents=True)
    (dir_b / "models").mkdir(parents=True)
    (dir_a / "models" / "m.yaml").write_text(
        "name: model-a\nfields: [F]\ntemplates:\n  - name: c\n    front: x\n    back: y\n"
    )
    (dir_b / "models" / "m.yaml").write_text(
        "name: model-b\nfields: [F]\ntemplates:\n  - name: c\n    front: x\n    back: y\n"
    )

    set_resources_dir(str(dir_a))
    assert "model-a" in _load_user_models()

    set_resources_dir(str(dir_b))
    # Cache should auto-invalidate because _resources_override changed
    anki_svc._user_models_cache = None
    anki_svc._user_models_cache_dir = None
    assert "model-b" in _load_user_models()
