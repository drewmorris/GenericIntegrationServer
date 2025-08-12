from __future__ import annotations

from typing import Type, Dict

from backend.destinations.base import DestinationBase

registry: Dict[str, Type[DestinationBase]] = {}

def register(name: str):
    def _decorator(cls: Type[DestinationBase]):
        registry[name] = cls
        return cls
    return _decorator

def get_destination(name: str) -> Type[DestinationBase]:
    if name not in registry:
        raise KeyError(f"Destination '{name}' not found")
    return registry[name]

# Eagerly import all destination modules so their @register decorators run
def _discover_destinations() -> None:
    import importlib, pkgutil
    for m in pkgutil.iter_modules(__path__):  # type: ignore[name-defined]
        if m.name.startswith("__"):
            continue
        importlib.import_module(f"{__name__}.{m.name}")

_discover_destinations() 