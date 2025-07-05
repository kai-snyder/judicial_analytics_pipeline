"""Package root: wires up logging & settings at import time."""
from pathlib import Path
import logging.config
import yaml

CONFIG_PATH = Path(__file__).with_suffix("").parent.parent / "config" / "logging.yaml"
logging.config.dictConfig(yaml.safe_load(CONFIG_PATH.read_text()))
