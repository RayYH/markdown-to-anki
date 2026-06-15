import os
import time
from pathlib import Path
from typing import Dict

import yaml

from markdown_to_anki.config import (
    DEFAULT_DECK,
    DEFAULT_MODEL,
    TIME_RANGE,
    MD_FOLDER,
)
from markdown_to_anki.helpers.file import file_get_contents, last_modified_time
from markdown_to_anki.helpers.path import read_resource, user_models_dir
from markdown_to_anki.helpers.store import (
    clear_all_anki_ids,
    get_all_anki_ids,
    get_anki_id,
    remove_anki_id,
    set_anki_id,
)
from markdown_to_anki.services.anki_api import AnkiApi
from markdown_to_anki.services.render import (
    markdown_metadata,
    markdown_to_html,
    split_multi_parts,
)


def _make_api(anki_url: str | None) -> AnkiApi:
    return AnkiApi(anki_uri=anki_url) if anki_url else AnkiApi()


def clean_notes(md_folder: str | None = None, anki_url: str | None = None):
    folder = md_folder or MD_FOLDER
    anki_api = _make_api(anki_url)
    ids = get_all_anki_ids(folder)
    clear_all_anki_ids(folder)
    anki_api.delete_notes(notes=ids)
    return True


def import_notes(md_folder: str | None = None, anki_url: str | None = None):
    folder = md_folder or MD_FOLDER
    anki_api = _make_api(anki_url)
    deck_names = anki_api.deck_names()
    updated_count = 0
    created_count = 0
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(".md") or file.lower().endswith(
                ".markdown"
            ):
                fullpath = os.path.join(root, file)
                last_modified = last_modified_time(filepath=fullpath)
                current = time.time()
                if current - last_modified > TIME_RANGE:
                    continue
                content = file_get_contents(fullpath)
                metadata = markdown_metadata(content)
                skip = metadata.get("skip") if metadata.get("skip") else 0
                if skip:
                    continue
                dn = (
                    metadata.get("deck")[0]
                    if metadata.get("deck")
                    else DEFAULT_DECK
                )
                if dn not in deck_names:
                    anki_api.create_deck(deck=dn)
                tags = metadata.get("tags") if metadata.get("tags") else []
                mn = (
                    metadata.get("model")[0]
                    if metadata.get("model")
                    else DEFAULT_MODEL
                )
                md = model_definition(mn)
                in_fields = (md.get("inOrderFields") if md else None) or []
                parts = split_multi_parts(content)
                for idx, (card_tags, part) in enumerate(parts, start=1):
                    fields = {
                        f: markdown_to_html(
                            part[i] if i < len(part) else "",
                            base_path=fullpath,
                        )
                        for i, f in enumerate(in_fields)
                    }
                    merged_tags = list(dict.fromkeys(tags + card_tags))
                    anki_id = get_anki_id(fullpath, idx)
                    if anki_id is not None:
                        try:
                            anki_api.notes_info([anki_id])
                        except Exception as e:
                            print(e)
                            remove_anki_id(fullpath, idx)
                            continue
                        old_deck_name = anki_api.card_deck_name(anki_id)
                        old_tags = anki_api.note_tags(anki_id)
                        anki_api.remove_tags(notes=[anki_id], tags=old_tags)
                        anki_api.add_tags(notes=[anki_id], tags=merged_tags)
                        if old_deck_name != dn:
                            anki_api.change_deck(cards=[anki_id], deck=dn)
                        anki_api.update_note_fields(anki_id, fields=fields)
                        updated_count += 1
                    else:
                        anki_id = anki_api.add_note(
                            deck_name=dn,
                            model_name=mn,
                            fields=fields,
                            tags=merged_tags,
                        )
                        set_anki_id(fullpath, idx, anki_id)
                        created_count += 1
    return {"notes created": created_count, "notes updated": updated_count}


MEDIA_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac", ".opus",
    ".mp4", ".mov", ".mkv", ".webm",
}


def import_medias(md_folder: str | None = None, anki_url: str | None = None):
    folder = md_folder or MD_FOLDER
    anki_api = _make_api(anki_url)
    created_count = 0
    for root, dirs, files in os.walk(folder):
        # ".trash" must match a directory segment, not a substring.
        dirs[:] = [d for d in dirs if d != ".trash"]
        for file in files:
            if os.path.splitext(file)[1].lower() not in MEDIA_EXTENSIONS:
                continue
            fullpath = os.path.abspath(os.path.join(root, file))
            anki_api.store_media_file_from_path(
                filename=os.path.basename(fullpath), path=fullpath
            )
            created_count += 1
    return {"media files created": created_count}


def m2a_basic_model() -> Dict:
    return {
        "modelName": "m2a-basic",
        "inOrderFields": ["Front", "Back"],
        "css": read_resource("anki/styles/basic.css"),
        "isCloze": False,
        "cardTemplates": [
            {
                "Name": "simple",
                "Front": read_resource("anki/templates/basic/front.html"),
                "Back": read_resource("anki/templates/basic/back.html"),
            }
        ],
    }


def m2a_basic_reverse_model() -> Dict:
    return {
        "modelName": "m2a-basic-reverse",
        "inOrderFields": ["Front", "Back"],
        "css": read_resource("anki/styles/basic.css"),
        "isCloze": False,
        "cardTemplates": [
            {
                "Name": "simple",
                "Front": read_resource("anki/templates/basic/front.html"),
                "Back": read_resource("anki/templates/basic/back.html"),
            },
            {
                "Name": "simple-reverse",
                "Front": read_resource(
                    "anki/templates/basic/reverse-front.html"
                ),
                "Back": read_resource("anki/templates/basic/reverse-back.html"),
            },
        ],
    }


def m2a_cloze_model() -> Dict:
    return {
        "modelName": "m2a-cloze",
        "inOrderFields": ["Text", "Extra"],
        "css": read_resource("anki/styles/basic.css"),
        "isCloze": True,
        "cardTemplates": [
            {
                "Name": "cloze",
                "Front": read_resource("anki/templates/cloze/front.html"),
                "Back": read_resource("anki/templates/cloze/back.html"),
            }
        ],
    }


def m2a_english_model() -> Dict:
    return {
        "modelName": "m2a-english",
        "inOrderFields": ["Word", "Audio", "Meaning"],
        "css": read_resource("anki/styles/english.css"),
        "isCloze": False,
        "cardTemplates": [
            {
                "Name": "word",
                "Front": read_resource(
                    "anki/templates/english/word-front.html"
                ),
                "Back": read_resource("anki/templates/english/word-back.html"),
            },
            {
                "Name": "meaning",
                "Front": read_resource(
                    "anki/templates/english/meaning-front.html"
                ),
                "Back": read_resource(
                    "anki/templates/english/meaning-back.html"
                ),
            },
        ],
    }


# Cache keyed on the resources dir so it auto-invalidates if the dir changes.
_user_models_cache: Dict | None = None
_user_models_cache_dir: Path | None = None


def _load_user_models() -> Dict:
    models_dir = user_models_dir()
    if not models_dir:
        return {}
    resources_dir = models_dir.parent
    models = {}
    yaml_files = sorted(
        list(models_dir.glob("*.yaml")) + list(models_dir.glob("*.yml"))
    )
    for yaml_file in yaml_files:
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if not data or "name" not in data or "fields" not in data:
            continue
        if "css_file" in data:
            css = (resources_dir / data["css_file"]).read_text(encoding="utf-8")
        else:
            css = data.get("css", "")
        templates = []
        for tmpl in data.get("templates", []):
            front = (
                (resources_dir / tmpl["front_file"]).read_text(encoding="utf-8")
                if "front_file" in tmpl
                else tmpl.get("front", "")
            )
            back = (
                (resources_dir / tmpl["back_file"]).read_text(encoding="utf-8")
                if "back_file" in tmpl
                else tmpl.get("back", "")
            )
            templates.append(
                {"Name": tmpl.get("name", "card"), "Front": front, "Back": back}
            )
        models[data["name"]] = {
            "modelName": data["name"],
            "inOrderFields": data["fields"],
            "css": css,
            "isCloze": data.get("is_cloze", False),
            "cardTemplates": templates,
        }
    return models


def _get_user_models() -> Dict:
    global _user_models_cache, _user_models_cache_dir
    from markdown_to_anki.helpers.path import get_resources_dir

    current_dir = get_resources_dir()
    if (
        _user_models_cache is None
        or _user_models_cache_dir != current_dir
    ):
        _user_models_cache = _load_user_models()
        _user_models_cache_dir = current_dir
    return _user_models_cache


def model_definition(model: str):
    user_models = _get_user_models()
    if model in user_models:
        return user_models[model]
    model = model.lower()
    if model == "m2a-basic":
        return m2a_basic_model()
    elif model == "m2a-cloze":
        return m2a_cloze_model()
    elif model == "m2a-english":
        return m2a_english_model()
    elif model == "m2a-basic-reverse":
        return m2a_basic_reverse_model()
    return None


def ensure_models(anki_url: str | None = None):
    updated, created = 0, 0
    anki_api = _make_api(anki_url)
    builtins = {
        m["modelName"]: m
        for m in [
            m2a_basic_model(),
            m2a_cloze_model(),
            m2a_english_model(),
            m2a_basic_reverse_model(),
        ]
    }
    # User-defined models override built-ins by name; new names are added.
    all_models = {**builtins, **_get_user_models()}
    existing_models = set(anki_api.model_names())
    for model in all_models.values():
        model_name = model.get("modelName")
        if model_name in existing_models:
            if model.get("css"):
                anki_api.update_model_styling(
                    name=model_name, css=model.get("css")
                )
            templates = model.get("cardTemplates")
            if templates:
                for template in templates:
                    anki_api.update_model_templates(
                        name=model_name,
                        templates={
                            template["Name"]: {
                                "Front": template["Front"],
                                "Back": template["Back"],
                            }
                        },
                    )
            updated += 1
        else:
            anki_api.create_model(**model)
            created += 1
    return {"created": created, "updated": updated}
