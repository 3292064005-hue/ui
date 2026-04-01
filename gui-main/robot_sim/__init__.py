from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path


__path__ = extend_path(__path__, __name__)

src_package_dir = Path(__file__).resolve().parent.parent / "src" / "robot_sim"
if src_package_dir.is_dir():
    __path__.append(str(src_package_dir))
