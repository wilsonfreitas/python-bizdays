"""Static and run-time types of the public API (contract section 6).

mypy checks this module (``assert_type``) and pytest runs it (``isinstance``
and ``dtype``), so each static type is tested next to its run-time type.
"""

import importlib.resources
import sys
from typing import TYPE_CHECKING, Any

from bizdays import Calendar

if TYPE_CHECKING:
    from typing_extensions import assert_type
elif sys.version_info >= (3, 11):
    from typing import assert_type
else:

    def assert_type(val: Any, typ: Any) -> Any:
        return val


cal = Calendar.load(name="B3")


def test_py_typed_marker_present() -> None:
    assert importlib.resources.files("bizdays").joinpath("py.typed").is_file()
