"""Session debug NDJSON + bench logger. Do not log secrets or tokens."""

from __future__ import annotations

import json
import time
from typing import Any

LOG_PATH = "/workspace/.cursor/debug-f51745.log"


def agent_debug(
	hypothesis_id: str,
	location: str,
	message: str,
	data: dict[str, Any] | None = None,
) -> None:
	payload = {
		"sessionId": "f51745",
		"hypothesisId": hypothesis_id,
		"location": location,
		"message": message,
		"timestamp": int(time.time() * 1000),
		"data": data or {},
	}
	line = json.dumps(payload, default=str) + "\n"
	try:
		with open(LOG_PATH, "a", encoding="utf-8") as f:
			f.write(line)
	except OSError:
		pass
	try:
		import frappe

		frappe.logger("books_integration").info(f"BOOKS_AGENT_DEBUG {line.strip()}")
	except Exception:
		pass
