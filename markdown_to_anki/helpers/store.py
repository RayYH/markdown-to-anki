import json
import os


def _sidecar_path(md_path: str) -> str:
    base, _ = os.path.splitext(md_path)
    return base + ".anki"


def get_anki_id(md_path: str, order: int):
    path = _sidecar_path(md_path)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    return data.get(str(order))


def set_anki_id(md_path: str, order: int, anki_id: int):
    path = _sidecar_path(md_path)
    data = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    data[str(order)] = anki_id
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def remove_anki_id(md_path: str, order: int):
    path = _sidecar_path(md_path)
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)
    data.pop(str(order), None)
    if data:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
    else:
        os.remove(path)


def get_all_anki_ids(md_folder: str) -> list:
    ids = []
    for root, dirs, files in os.walk(md_folder):
        for file in files:
            if file.endswith(".anki"):
                with open(os.path.join(root, file)) as f:
                    data = json.load(f)
                ids.extend(data.values())
    return ids


def clear_all_anki_ids(md_folder: str):
    for root, dirs, files in os.walk(md_folder):
        for file in files:
            if file.endswith(".anki"):
                os.remove(os.path.join(root, file))
