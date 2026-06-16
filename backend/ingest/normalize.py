"""Read and write normalized emails as JSONL.

JSONL (one JSON object per line) is the intermediate format every ingest
source produces, so the rest of the pipeline is independent of how emails
were obtained (Outlook COM, PST export, .eml/.msg, or synthetic samples).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.schemas import Email


def save_emails(emails: Iterable[Email], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for email in emails:
            f.write(email.model_dump_json())
            f.write("\n")
            count += 1
    return count


def load_emails(path: Path) -> list[Email]:
    emails: list[Email] = []
    if not path.exists():
        return emails
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            emails.append(Email.model_validate_json(line))
    return emails
