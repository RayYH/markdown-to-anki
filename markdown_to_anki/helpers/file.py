import os.path


def file_get_contents(filepath: str) -> str:
    with open(filepath) as f:
        return f.read()


def last_modified_time(filepath: str) -> float:
    return os.path.getmtime(filepath)
