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
			try:
				# Convert non-serializable args to strings for JSON safety
				serializable = []
				for a in record.args if isinstance(record.args, (list, tuple)) else [record.args]:
					try:
						json.dumps(a)
						serializable.append(a)
					except Exception:
						serializable.append(str(a))
				payload["args"] = mask_secrets(tuple(serializable))
			except Exception:
				payload["args"] = "<unserializable>"
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