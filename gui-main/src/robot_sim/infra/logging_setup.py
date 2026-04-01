from __future__ import annotations
from pathlib import Path
import logging.config
import yaml

def setup_logging(logging_yaml: str | Path | None = None) -> None:
    if logging_yaml is None:
        logging.basicConfig(level=logging.INFO)
        return
    path = Path(logging_yaml)
    if not path.exists():
        logging.basicConfig(level=logging.INFO)
        return
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)
