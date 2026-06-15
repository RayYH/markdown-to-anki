import json
import os
import subprocess
from urllib.parse import urlparse
import urllib.request


def run_bash(bash_command: str) -> dict:
    try:
        process = subprocess.Popen(
            bash_command, stdout=subprocess.PIPE, shell=True
        )
        output, error = process.communicate()
        output = output.decode("utf8").strip() if output else None
        error = error.decode("utf8").strip() if error else None
    except FileNotFoundError:
        output, error = None, "bash command not found"
    return {"output": output, "error": error}


def parse_basename_from_url(url: str) -> str:
    return os.path.basename(urlparse(url).path)


def normalize_filename_from_uri(base_url: str, url: str):
    return url.replace(base_url, "").strip("/").replace("/", "_")


def sink_file(url: str, filename: str):
    urllib.request.urlretrieve(url, filename)


def json_dumps(d: dict):
    print(json.dumps(d, sort_keys=True, indent=4))
