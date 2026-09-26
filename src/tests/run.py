# ai-generated: 80% - Claude (AI assistant) generated this runner under the student's direction (design, review, and verification against the running service).
"""Entry point for `docker compose --profile tests run tests` (L2-STRETCH-3 / CHECKS.md).

Runs the pytest suite in this package and prints exactly one summary line as the LAST line of
stdout: `ITSMLAB-TESTS: passed=<n> failed=<n>`. A pytest hook implementation collects the pass/
fail counts from each test's "call" phase report so the line reflects real outcomes rather than
a parsed copy of pytest's own (differently formatted, and not guaranteed-last) summary line.
"""
import os
import sys

import pytest


class _Counter:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def pytest_runtest_logreport(self, report):
        if report.when != "call":
            return
        if report.passed:
            self.passed += 1
        elif report.failed:
            self.failed += 1


def main() -> int:
    counter = _Counter()
    test_dir = os.path.dirname(os.path.abspath(__file__))
    exit_code = pytest.main(["-q", test_dir], plugins=[counter])
    # Flush pytest's own report before printing the required line, so ours is unambiguously last.
    sys.stdout.flush()
    print(f"ITSMLAB-TESTS: passed={counter.passed} failed={counter.failed}")
    sys.stdout.flush()
    return 0 if counter.failed == 0 and int(exit_code) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
