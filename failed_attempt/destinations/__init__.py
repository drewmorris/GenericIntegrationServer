from __future__ import annotations

import importlib
import pkgutil
from typing import Type, Dict, Optional

from backend.destinations.base import DestinationBase

# Lazy-loaded registry: only populated when destinations are actually requested
registry: Dict[str, Type[DestinationBase]] = {}

# Module mapping for lazy loading - add new destinations here
DESTINATION_MODULES = {
    "cleverbrag": "backend.destinations.cleverbrag", 
    "csvdump": "backend.destinations.csvdump",
    "onyx": "backend.destinations.onyx",
    # Add future destinations here without breaking existing ones
}

def register(name: str):
    """Decorator to register destinations in the registry"""
    def _decorator(cls: Type[DestinationBase]):
        registry[name] = cls
        return cls
    return _decorator

def _lazy_load_destination(name: str) -> Optional[Type[DestinationBase]]:
    """Lazily load a destination module and return its registered class"""
    if name in registry:
        return registry[name]
    
    # Check if we have a module mapping for this destination
    if name not in DESTINATION_MODULES:
        return None
    
    try:
        module_path = DESTINATION_MODULES[name]
        importlib.import_module(module_path)
        # After importing, the @register decorator should have added it to registry
        return registry.get(name)
    except ImportError as e:
        # Log but don't crash - missing dependencies for unused connectors is OK
        print(f"⚠️  Could not load destination '{name}': {e}")
        print(f"   This is OK if you're not using the {name} connector.")
        return None
    except Exception as e:
        print(f"❌ Unexpected error loading destination '{name}': {e}")
        return None

def get_destination(name: str) -> Type[DestinationBase]:
    """Get destination class, loading it lazily if needed"""
    destination_class = _lazy_load_destination(name)
    if destination_class is None:
        available = list_available_destinations()
        raise KeyError(f"Destination '{name}' not found. Available: {available}")
    return destination_class

def list_available_destinations() -> list[str]:
    """List all available destinations (tries to load them but handles errors gracefully)"""
    available = []
    for name in DESTINATION_MODULES.keys():
        if _lazy_load_destination(name) is not None:
            available.append(name)
    return available

# For backward compatibility with existing code that might access registry directly
def get_registry() -> Dict[str, Type[DestinationBase]]:
    """Get the full registry, loading all available destinations"""
    for name in DESTINATION_MODULES.keys():
        _lazy_load_destination(name)  # This populates the registry
    return registry 