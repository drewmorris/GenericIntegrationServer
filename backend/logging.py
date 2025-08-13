import json
import logging
import sys
from datetime import datetime

from backend.security.redact import mask_secrets


class JsonFormatter(logging.Formatter):
	def format(self, record: logging.LogRecord) -> str:
		payload = {
			"timestamp": datetime.utcnow().isoformat() + 'Z',
			"level": record.levelname,
			"logger": record.name,
			"message": record.getMessage(),
		}
		if record.args:
			payload["args"] = mask_secrets(record.args)
		if record.exc_info:
			payload["exc_info"] = self.formatException(record.exc_info)
		return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
	root = logging.getLogger()
	root.setLevel(level)
	for h in list(root.handlers):
		root.removeHandler(h)
	h = logging.StreamHandler(sys.stdout)
	h.setLevel(level)
	h.setFormatter(JsonFormatter())
	root.addHandler(h) 