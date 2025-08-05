"""Compatibility shim so imports like `onyx.utils` work.

This package redirects to `connectors.onyx` sub-packages, allowing us to
retain legacy import paths without copying code.
"""
import importlib
import sys

_base = importlib.import_module("connectors.onyx")
# Register the base module as 'onyx'
sys.modules[__name__] = _base

# Expose key subpackages under onyx.*
for sub in ("connectors", "configs", "utils", "db"):
    target = f"connectors.onyx.{sub}"
    try:
        sys.modules[f"{__name__}.{sub}"] = importlib.import_module(target)

        # also expose nested modules like configs.constants
        if sub == "configs":
            try:
                const_mod = importlib.import_module(f"{target}.constants")
                sys.modules[f"{__name__}.configs.constants"] = const_mod
            except ModuleNotFoundError:
                # create minimal placeholder
                import types, enum

                const_mod = types.ModuleType(f"{__name__}.configs.constants")

                class _DocumentSource(str, enum.Enum):
                    INGESTION_API = "ingestion_api"

                setattr(const_mod, "DocumentSource", _DocumentSource)
                setattr(const_mod, "PUBLIC_DOC_PAT", r"public")
                sys.modules[f"{__name__}.configs.constants"] = const_mod
        if sub == "db":
            try:
                enums_mod = importlib.import_module(f"{target}.enums")
                sys.modules[f"{__name__}.db.enums"] = enums_mod
            except ModuleNotFoundError:
                pass
    except ModuleNotFoundError:
        pass 