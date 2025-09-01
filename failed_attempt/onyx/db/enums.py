# Minimal DB enums stub - credential testing doesn't need complex enums

from enum import Enum as PyEnum
from typing import Any
from pydantic_core import core_schema


class AccessType(str, PyEnum):
    """AccessType enum - matches LegacyCode values for compatibility"""
    PUBLIC = "public"
    PRIVATE = "private"
    SYNC = "sync"
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler) -> core_schema.CoreSchema:
        return core_schema.any_schema()


class IndexModelStatus(str, PyEnum):
    """IndexModelStatus enum - matches LegacyCode values for compatibility"""
    PAST = "PAST"
    PRESENT = "PRESENT"
    FUTURE = "FUTURE"
    
    def is_current(self) -> bool:
        return self == IndexModelStatus.PRESENT
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler) -> core_schema.CoreSchema:
        return core_schema.any_schema()
