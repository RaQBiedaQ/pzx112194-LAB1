---
lab5_triage:
  image: ghcr.io/raqbiedaq/pzx112194-lab1@sha256:b6186785e5af9fa2f17e8eb0484e5d33a589249c05ed98e3995ac35d83448137
  sarif_receipt: 379
---
<!-- ai-generated: 70% - Claude read the five SARIF files and drafted the rows; the student reviewed each decision and the bake-off paragraph against their own matrix. -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12). The gates (`deps`, `secrets`, `image`) were green on `main` from the first run: the Dockerfile already upgrades the base image's packages after the `FROM` and removes pip after installing, so no entry sits in `.trivyignore` or `.gitleaksignore`. Everything below comes from the reporting scanners and from the three medium-severity pins that the dependency scanners report below the gate's HIGH threshold.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2025-71176 | fix | pytest 8.4.2 in requirements.txt line 4 has a medium advisory fixed in 9.0.3; the pin is raised to 9.0.3. pytest is the test runner only, and src/tests/run.py uses only pytest.main and a report hook, which are unchanged. |
| trivy | CVE-2024-47081 | fix | requests 2.32.3 in requirements.txt line 5 can leak .netrc credentials through a crafted URL; fixed in 2.32.4. The pin is raised to 2.33.0, which also carries the fix for CVE-2026-25645. |
| trivy | CVE-2026-25645 | fix | requests 2.32.3 has this medium advisory, fixed in 2.33.0. The pin is raised to 2.33.0 in requirements.txt; requests is used only by the test fixtures in src/tests/conftest.py. |
| grype | GHSA-6w46-j5rx-g56g-pytest | fix | The GitHub advisory id of the same pytest 8.4.2 finding as CVE-2025-71176 (Trivy): closed by the same pin change to 9.0.3 in requirements.txt. |
| grype | GHSA-9hjg-9r4m-mvj7-requests | fix | The GitHub advisory id of the requests 2.32.3 finding CVE-2024-47081 (Trivy): closed by raising requests to 2.33.0 in requirements.txt. |
| grype | GHSA-gc5v-m9x4-r6x2-requests | fix | The GitHub advisory id of the requests 2.32.3 finding CVE-2026-25645 (Trivy): closed by raising requests to 2.33.0 in requirements.txt. |
| osv-scanner | CVE-2024-47081 | fix | requests 2.32.3, the same finding as in Trivy and Grype; OSV-Scanner reports it twice (two lock entries for requirements.txt), and the one pin change to 2.33.0 removes both. |
| osv-scanner | CVE-2025-71176 | fix | pytest 8.4.2, the same finding as in Trivy and Grype; reported twice for the same file, removed by the pin change to 9.0.3 in requirements.txt. |
| osv-scanner | CVE-2026-25645 | fix | requests 2.32.3, the same finding as in Trivy and Grype; reported twice for the same file, removed by raising requests to 2.33.0. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | The Dockerfile (line 31) has no USER, so the service runs as root in its container. The finding is right. I accept it for now: the SQLite file lives on a named volume at /data, and switching users needs the volume's ownership proved against the course's compose contract. Revisit by 2026-12-31. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | false-positive | agent/prom_mcp.py line 34 builds the request URL from the PROMETHEUS_URL environment variable that the operator sets on their own laptop, not from user input, and the course's Prometheus server is read-only. It is not part of the image (the Dockerfile copies src/ only). |

## Bake-off

Measured on the canary set lab5-canary (9 seeded defects: 4 code, 3 secrets, 2 vulnerable dependencies) with bakeoff.py on the five committed SARIF files. Results (TP/FP/FN, precision, recall, F1): gitleaks 3/0/6, 1.00, 0.33, 0.50; grype 2/0/7, 1.00, 0.22, 0.36; osv-scanner 2/0/7, 1.00, 0.22, 0.36; semgrep 4/3/5, 0.57, 0.44, 0.50; trivy 3/0/6, 1.00, 0.33, 0.50. No tool finds more than 4 of 9 defects, and the specialists only see their own class: grype and osv-scanner catch both vulnerable dependencies (cryptography and starlette), gitleaks catches the three planted credentials, semgrep catches the code defects it has rules for (shell=True in attachment_export.py, yaml.load in rules_loader.py) plus two secrets. Trivy is the surprise: it found both dependencies and the JWT in cmdb_token.py, so one tool covers two classes. The path traversal (attachment_read.py) and the SSRF (webhook_relay.py) were found by nobody, which is the real gap in this pipeline. Semgrep is the only noisy tool: its 3 false positives (sha1 in etag.py and two SQL rules on the same line of ticket_counts.py) cost precision 0.57, so it should be advisory, not a gate. I gate on Trivy (dependencies and image, 1.00 precision, broadest coverage) and gitleaks (secrets, no false positives), which matches the pipeline. Caveat: the defects are seeded and easy, so these recalls are upper bounds; on real code every tool would likely miss more, and FP counts would grow.
