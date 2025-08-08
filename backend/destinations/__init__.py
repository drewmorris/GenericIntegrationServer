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