import datetime
import os.path
import time


def file_get_contents(filepath: str) -> str:
    with open(filepath) as f:
        return f.read()


def last_modified_time(filepath: str):
    return datetime.datetime.strptime(
        time.ctime(os.path.getmtime(filepath)), "%a %b %d %H:%M:%S %Y"
    ).timestamp()
