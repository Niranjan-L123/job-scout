import os

import yaml


def load_config(path=None):
    path = path or os.environ.get("JOB_SCOUT_CONFIG", "config.yaml")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)
