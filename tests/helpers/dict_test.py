from markdown_to_anki.helpers.dict import safe_get


def test_safe_get():
    d = {"a": {"b": "c"}, "d.e": "f", "g": {"h": {"i": {"j": "h"}}}}

    assert safe_get(d, "a") == {"b": "c"}
    assert safe_get(d, "d.e") == "f"
    assert safe_get(d, "g.h.i.j") == "h"
    assert safe_get(d, "non", "default") == "default"

    result = {
        "action": "modelStyling",
        "version": 6,
        "params": {"modelName": "Basic (and reversed card)"},
    }
    assert safe_get(result, "params.modelName") == "Basic (and reversed card)"
