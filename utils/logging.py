"""Central logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(base_dir: Path) -> None:
    """Configure a console and local rotating application log once."""
    if logging.getLogger().handlers:
        return
    log_dir = base_dir / "instance"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "caregiver_management.log", encoding="utf-8"),
        ],
    )
