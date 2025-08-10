from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Iterable, Dict, Any

from backend.destinations.base import DestinationBase
from backend.destinations import register

logger = logging.getLogger(__name__)


@register("csv")
class CsvDumpDestination(DestinationBase):
    name = "csv"

    def __init__(self) -> None:
        self.dump_dir = Path(os.getenv("CSV_DUMP_DIR", "./csv_dumps"))
        self.dump_dir.mkdir(parents=True, exist_ok=True)

    async def send(self, *, payload: Iterable[Dict[str, Any]], profile_config: dict[str, Any]) -> None:  # noqa: D401
        for doc in payload:
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
            import uuid, copy
            def _stringify(obj):  # noqa: D401
                if isinstance(obj, dict):
                    return {k: _stringify(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_stringify(v) for v in obj]
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                return obj

            safe_doc = _stringify(copy.deepcopy(doc))
            file_path = self.dump_dir / f"{safe_doc.get('id', 'doc')}_{ts}.json"
            file_path.write_text(json.dumps(safe_doc, ensure_ascii=False, indent=2))
            logger.info("Wrote document to %s", file_path) 