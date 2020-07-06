import os

import yaml

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(PROJECT_DIR, "config.yaml"), "r") as config_file:
    config = yaml.safe_load(config_file.read())
