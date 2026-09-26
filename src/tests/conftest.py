# ai-generated: 80% - Claude (AI assistant) generated this test fixture module under the student's direction (design, review, and verification against the running service).
"""Shared fixtures for the own-tests suite (L2-STRETCH-3): a base URL and a short health-poll
retry so a cold `docker compose up` does not race the first request, per the course scaffold's
own note in docker-compose.yml."""
import os
import time

import pytest
import requests


def _base_url() -> str:
    return os.environ.get("SVCDESK_URL", "http://svcdesk:8080")


@pytest.fixture(scope="session", autouse=True)
def _wait_for_service():
    url = _base_url() + "/health"
    deadline = time.monotonic() + 30
    last_error = None
    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"svcdesk never became healthy at {url}: {last_error}")


@pytest.fixture(scope="session")
def base_url() -> str:
    return _base_url()


@pytest.fixture(scope="session")
def http():
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()
