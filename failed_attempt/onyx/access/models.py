# Minimal access models stub - credential testing doesn't need complex access control

from typing import Optional, Set, Any
from pydantic import BaseModel
from pydantic_core import core_schema


class ExternalAccess(BaseModel):
    """Minimal Pydantic-compatible stub for ExternalAccess - credential testing doesn't need access control"""
    
    external_access_emails: Optional[Set[str]] = None
    external_access_group_ids: Optional[Set[str]] = None
    is_public: bool = False
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler) -> core_schema.CoreSchema:
        return core_schema.any_schema()