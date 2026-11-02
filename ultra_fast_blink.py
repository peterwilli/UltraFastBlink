"""Ultra Fast Blink SASpro entry point.

Install this file together with the ultra_fast_blink folder.
Made with love by Emerald — https://emerald.show
"""
SCRIPT_NAME = "Ultra Fast Blink Comparator"
SCRIPT_GROUP = "Tools"
SCRIPT_ID = "setiastro.ultra-fast-blink"

import importlib.util
from importlib import import_module
from pathlib import Path
import sys
import uuid

# A fresh package per load refreshes helpers without changing existing windows.
_package_name = "_saspro_ultra_fast_blink_" + uuid.uuid4().hex
_package_dir = Path(__file__).resolve().with_suffix("")
_spec = importlib.util.spec_from_file_location(
    _package_name, _package_dir / "__init__.py",
    submodule_search_locations=[str(_package_dir)],
)
_package = importlib.util.module_from_spec(_spec)
sys.modules[_package_name] = _package
try:
    _spec.loader.exec_module(_package)
    _run = import_module(_package_name + "._integration").run
except Exception:
    for _name in list(sys.modules):
        if _name == _package_name or _name.startswith(_package_name + "."):
            del sys.modules[_name]
    raise


def run(ctx):
    return _run(ctx)
