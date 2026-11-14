# ai-generated: 80% - Claude wrote these test cases for semgrep/rules.yml; the student reviewed them
import sqlite3
from datetime import datetime, timezone


def resolve_now(request):
    # ruleid: svcdesk-direct-clock-read
    return datetime.now(timezone.utc)


def create_ticket(request):
    # ruleid: svcdesk-direct-clock-read
    now = datetime.now(timezone.utc)
    return now


def create_ticket_ok(request):
    # ok: svcdesk-direct-clock-read
    now = resolve_now(request)
    return now


def open_database_in_a_handler(path):
    # ruleid: svcdesk-sqlite-connect
    return sqlite3.connect(path)


def read_tickets(storage):
    # ok: svcdesk-sqlite-connect
    return storage.list_all()
