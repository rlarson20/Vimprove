from datetime import datetime
from pathlib import Path
import json


class ErrorLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.errors = []

    def log_error(
        self,
        source: str,
        error_type: str,
        message: str,
        details: dict[str, any] | None = None,
    ):
        """Log an error that occurred during processing."""
        self.errors.append(
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": source,
                "error_type": error_type,
                "message": message,
                "details": details or {},
            }
        )

    def save(self):
        """Save errors to JSON file."""
        if not self.errors:
            # Don't create file if no errors
            return

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing errors if file exists
        existing_errors = []
        if self.log_path.exists():
            with open(self.log_path, encoding="utf-8") as f:
                existing_errors = json.load(f)

        # Append new errors
        all_errors = existing_errors + self.errors

        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(all_errors, f, indent=2, ensure_ascii=False)

        print(f"\n⚠️  Logged {len(self.errors)} errors to {self.log_path}")

    def has_errors(self) -> bool:
        return len(self.errors) > 0
