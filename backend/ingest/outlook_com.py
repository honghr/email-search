"""Ingest emails from the local Outlook desktop client (Windows).

Reads the live mailbox through the Outlook COM API. Nothing leaves the machine
and no cloud authorization is required. You can point it at a specific folder
(e.g. a hand-curated "EmailSearch" folder) to index only the emails you want.

Usage:
    python -m ingest.outlook_com --folder EmailSearch --out ../data/emails.jsonl
    python -m ingest.outlook_com --limit 2000   # whole mailbox, newest first

Requires the `pywin32` package and Outlook installed.
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

from app.schemas import Email
from ingest.normalize import save_emails

# Outlook MAPI item class for mail items.
OL_MAIL_ITEM = 43
_WS = re.compile(r"[ \t\u00a0]+")
_NL = re.compile(r"\n{3,}")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS.sub(" ", text)
    text = _NL.sub("\n\n", text)
    return text.strip()


def _to_datetime(value) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime(value.year, value.month, value.day,
                        value.hour, value.minute, value.second)
    except Exception:
        return None



def _iter_mail_items(folder, collected: list, limit: int):
    """Depth-first walk over a folder tree, collecting mail items.

    Within each folder, items are sorted by received time (newest first) so
    that the most recent mail is preferred. A final global sort in `extract`
    guarantees the overall newest `limit` across all folders.
    """
    try:
        items = folder.Items
        try:
            items.Sort("[ReceivedTime]", True)  # descending: newest first
        except Exception:
            pass
    except Exception:
        items = None
    if items is not None:
        taken = 0
        for item in items:
            if taken >= limit:
                break
            try:
                if getattr(item, "Class", None) != OL_MAIL_ITEM:
                    continue
                collected.append(item)
                taken += 1
            except Exception:
                continue
    for sub in folder.Folders:
        _iter_mail_items(sub, collected, limit)


def _recipients(item) -> list[str]:
    out: list[str] = []
    try:
        for r in item.Recipients:
            addr = getattr(r, "Address", "") or getattr(r, "Name", "")
            if addr:
                out.append(str(addr))
    except Exception:
        pass
    return out


def _attachments(item) -> list[str]:
    out: list[str] = []
    try:
        for a in item.Attachments:
            name = getattr(a, "FileName", "")
            if name:
                out.append(str(name))
    except Exception:
        pass
    return out


# MAPI property tag for PR_INTERNET_MESSAGE_ID (string).
_PROP_INTERNET_MESSAGE_ID = "http://schemas.microsoft.com/mapi/proptag/0x1035001F"


def _internet_message_id(item) -> str:
    try:
        pa = item.PropertyAccessor
        return str(pa.GetProperty(_PROP_INTERNET_MESSAGE_ID) or "")
    except Exception:
        return ""


def _find_folder(namespace, name: str):
    """Find the first folder matching `name` (case-insensitive) anywhere."""
    target = name.strip().lower()

    def walk(folder):
        try:
            if (folder.Name or "").strip().lower() == target:
                return folder
        except Exception:
            pass
        for sub in folder.Folders:
            found = walk(sub)
            if found is not None:
                return found
        return None

    for store in namespace.Stores:
        try:
            root = store.GetRootFolder()
        except Exception:
            continue
        found = walk(root)
        if found is not None:
            return found
    return None


def _item_to_email(item, idx: int) -> Email | None:
    try:
        entry_id = getattr(item, "EntryID", None) or f"item-{idx}"
        imid = _internet_message_id(item)
        return Email(
            id=str(entry_id),
            subject=_clean(getattr(item, "Subject", "")),
            body=_clean(getattr(item, "Body", "")),
            sender=str(getattr(item, "SenderEmailAddress", "") or ""),
            sender_name=str(getattr(item, "SenderName", "") or ""),
            recipients=_recipients(item),
            date=_to_datetime(getattr(item, "ReceivedTime", None)),
            attachments=_attachments(item),
            folder=str(getattr(getattr(item, "Parent", None), "Name", "") or ""),
            internet_message_id=imid,
        )
    except Exception:
        return None


def extract(limit: int, folder_name: str | None = None) -> list[Email]:
    import win32com.client  # imported lazily; Windows + Outlook only

    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")

    raw_items: list = []
    if folder_name:
        folder = _find_folder(namespace, folder_name)
        if folder is None:
            raise SystemExit(f"Folder '{folder_name}' not found in Outlook")
        _iter_mail_items(folder, raw_items, limit)
    else:
        for store in namespace.Stores:
            try:
                root = store.GetRootFolder()
            except Exception:
                continue
            _iter_mail_items(root, raw_items, limit)

    def _received(item):
        return _to_datetime(getattr(item, "ReceivedTime", None)) or datetime.min

    raw_items.sort(key=_received, reverse=True)
    raw_items = raw_items[:limit]

    emails: list[Email] = []
    for idx, item in enumerate(raw_items):
        email = _item_to_email(item, idx)
        if email is not None:
            emails.append(email)
    return emails


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest emails from Outlook")
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--folder", type=str, default=None,
                        help="Only read this folder (e.g. EmailSearch)")
    parser.add_argument("--out", type=str, default="../data/emails.jsonl")
    args = parser.parse_args()

    emails = extract(args.limit, args.folder)
    out_path = Path(__file__).resolve().parent.parent / args.out
    written = save_emails(emails, out_path.resolve())
    where = f"folder '{args.folder}'" if args.folder else "mailbox"
    print(f"Extracted {written} emails from {where} -> {out_path.resolve()}")


if __name__ == "__main__":
    main()

