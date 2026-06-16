"""Open an email in the local Outlook desktop client by its EntryID.

Browsers cannot launch Outlook directly, so the frontend calls this endpoint
and the backend (running on the same machine) uses the Outlook COM API to
display the exact message. No cloud authorization is required.
"""
from __future__ import annotations


def open_email(entry_id: str) -> None:
    import pythoncom
    import win32com.client

    # The API runs the request on a worker thread; COM must be initialised.
    pythoncom.CoInitialize()
    try:
        ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        item = ns.GetItemFromID(entry_id)
        item.Display()
    finally:
        pythoncom.CoUninitialize()
