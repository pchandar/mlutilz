import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, List, Optional, Union


LOGGER = logging.getLogger(__name__)


def is_in_jupyter_notebook():
    # pylint: disable=import-outside-toplevel
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
        jupyter = shell in ["ZMQInteractiveShell", "Shell"]
    except ImportError:
        jupyter = False

    return jupyter


def flatten_list(nested_list):
    """Flatten an arbitrarily nested list, without recursion (to avoid
    stack overflows). Returns a new list, the original list is unchanged.
    >> list(flatten_list([1, 2, 3, [4], [], [[[[[[[[[5]]]]]]]]]]))
    [1, 2, 3, 4, 5]
    >> list(flatten_list([[1, 2], 3]))
    [1, 2, 3]
    """
    nested_list = deepcopy(nested_list)

    while nested_list:
        sublist = nested_list.pop(0)

        if isinstance(sublist, list):
            nested_list = sublist + nested_list
        else:
            yield sublist


def always_return_list(val) -> Optional[List[Any]]:
    return val if val is None or isinstance(val, list) else [val]


def import_class_from_string(name: str):
    components = name.split(".")
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def get_qualified_class_name(o, is_type: bool = False):
    klass = o.__class__ if not is_type else o
    module = klass.__module__
    if module == "__builtin__" or module == "builtins":
        return klass.__name__  # avoid outputs like '__builtin__.str'
    return module + "." + klass.__name__


def snake_case_id(name):
    # credit to https://stackoverflow.com/a/1176023/11676752
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1-\2", name)
    s1 = re.sub(r"\.|-", r"_", s1)
    return re.sub("([a-z0-9])([A-Z])", r"\1-\2", s1).lower()


def filesystem(loc: Union[str, Path]):
    from gcsfs import GCSFileSystem

    return GCSFileSystem() if str(loc).startswith("gs") else None
