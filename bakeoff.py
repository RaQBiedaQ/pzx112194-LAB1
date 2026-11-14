# ai-generated: 70% - Claude wrote this from CI-SPEC.md section 3 (P-14 to P-23) and checked it against the practice set's expected.json; the student reviewed the rules it implements.
"""bakeoff.py - scanner SARIF + a labels file -> a per-tool confusion matrix (CI-SPEC.md P-23).

    python3 bakeoff.py --labels labels.json a.sarif b.sarif > bakeoff.json

Standard library only (it runs as `python3 -S -E bakeoff.py`). The rules are those of CI-SPEC.md section 3:
P-15 tools, P-16 results, P-17 paths and scope, P-18 lines, P-19 classes, P-20 matching, P-21 counting,
P-22 scores.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from urllib.parse import unquote

# P-19: the ten course classes and their CWE numbers.
CLASS_CWES: dict[str, frozenset[int]] = {
    "secret": frozenset({259, 260, 321, 798}),
    "injection": frozenset({74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336}),
    "deserialization": frozenset({502}),
    "weak-crypto": frozenset({261, 326, 327, 328, 330, 331, 338, 759, 760, 916}),
    "insecure-transport": frozenset({295, 297, 319, 322, 757}),
    "path-traversal": frozenset({22, 23, 35, 36, 73}),
    "ssrf": frozenset({918}),
    "vulnerable-dependency": frozenset({937, 1035, 1104, 1395}),
    "misconfiguration": frozenset({16, 215, 250, 489, 668, 732, 1188}),
    "access-control": frozenset({284, 285, 639, 862, 863}),
}

SEMGREP_NAMES = {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}
FIXED_TOOLS = {"trivy", "grype", "osv-scanner", "gitleaks"}
TRIVY_TAG_CLASSES = {"vulnerability": "vulnerable-dependency", "secret": "secret", "misconfiguration": "misconfiguration"}
CWE_RE = re.compile(r"(?<![A-Za-z0-9])cwe-([0-9]+)", re.IGNORECASE | re.ASCII)
TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def tool_id(run: dict) -> str:
    """P-15."""
    name = as_dict(as_dict(run.get("tool")).get("driver")).get("name")
    if not isinstance(name, str):
        return "unknown"
    name = name.strip()
    lowered = name.lower()
    if lowered in FIXED_TOOLS:
        return lowered
    if lowered in SEMGREP_NAMES:
        return "semgrep"
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "unknown"


def result_path(uri: str) -> str:
    """P-17: decode, drop a file:// prefix, drop one leading ./ ."""
    path = unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    if path.startswith("./"):
        path = path[2:]
    return path


def in_set(path: str, root: str):
    """P-17: the file is the path from the last component equal to the set root, or None."""
    parts = path.split("/")
    last = None
    for i, part in enumerate(parts):
        if part == root:
            last = i
    if last is None:
        return None
    return "/".join(parts[last:])


def result_lines(physical: dict):
    """P-18: (start, end) or None."""
    region = as_dict(physical.get("region"))
    start = region.get("startLine")
    if not is_int(start) or start < 1:
        return None
    end = region.get("endLine")
    if not is_int(end) or end < start:
        end = start
    return (start, end)


def find_rule(run: dict, rule_id):
    """P-19: the first rules[] entry of the same run whose id equals the ruleId."""
    if not isinstance(rule_id, str):
        return {}
    for rule in as_list(as_dict(as_dict(run.get("tool")).get("driver")).get("rules")):
        if isinstance(rule, dict) and rule.get("id") == rule_id:
            return rule
    return {}


def string_tags(obj: dict) -> list[str]:
    return [t for t in as_list(as_dict(obj.get("properties")).get("tags")) if isinstance(t, str)]


def result_classes(tid: str, result: dict, rule: dict) -> set[str]:
    """P-19: the classes of one result."""
    own = as_dict(result.get("properties")).get("class")
    if isinstance(own, str) and own in CLASS_CWES:
        return {own}
    if tid == "gitleaks":
        return {"secret"}
    if tid in ("grype", "osv-scanner"):
        return {"vulnerable-dependency"}
    if tid == "trivy":
        found = {c for c in (TRIVY_TAG_CLASSES.get(t.lower()) for t in string_tags(rule)) if c}
        if found:
            return found
    classes: set[str] = set()
    for tag in string_tags(result) + string_tags(rule):
        for match in CWE_RE.finditer(tag):
            number = int(match.group(1))
            for cls, numbers in CLASS_CWES.items():
                if number in numbers:
                    classes.add(cls)
    return classes or {"other"}


def normalise_package(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.lower())


def names_package(message, package) -> bool:
    """P-20: some token of message.text equals the package name (PEP 503)."""
    text = as_dict(message).get("text")
    if not isinstance(text, str) or not isinstance(package, str):
        return False
    wanted = normalise_package(package)
    for token in TOKEN_RE.findall(text):
        token = token.strip("._-")
        if token and normalise_package(token) == wanted:
            return True
    return False


def keep_result(result: dict) -> bool:
    """P-16: kind absent, null or exactly 'fail'; suppressions absent, null or empty."""
    kind = result.get("kind")
    if kind is not None and kind != "fail":
        return False
    return not result.get("suppressions")


def matches(defect: dict, res: dict) -> bool:
    """P-20."""
    if res["file"] != defect.get("file") or defect.get("class") not in res["classes"]:
        return False
    if defect.get("class") == "vulnerable-dependency":
        return names_package(res["message"], defect.get("package"))
    lines = res["lines"]
    d_start, d_end = defect.get("start_line"), defect.get("end_line")
    if lines is None or not is_int(d_start) or not is_int(d_end):
        return False
    return lines[0] <= d_end and d_start <= lines[1]


def score(num: int, den: int):
    return None if den == 0 else round(num / den, 4)


def confusion_matrix(labels: dict, sarif_documents: list) -> dict:
    """The matrix of P-21 and P-22 for the labels (P-14) and the parsed SARIF documents."""
    root = labels["set"]
    defects = [d for d in as_list(labels.get("defects")) if isinstance(d, dict)]
    per_tool: dict[str, list[dict]] = {}
    for document in sarif_documents:
        for run in as_list(as_dict(document).get("runs")):
            if not isinstance(run, dict):
                continue
            tid = tool_id(run)
            bucket = per_tool.setdefault(tid, [])
            for result in as_list(run.get("results")):
                if not isinstance(result, dict) or not keep_result(result):
                    continue
                locations = as_list(result.get("locations"))
                if not locations or not isinstance(locations[0], dict):
                    continue
                physical = as_dict(locations[0].get("physicalLocation"))
                uri = as_dict(physical.get("artifactLocation")).get("uri")
                if not isinstance(uri, str) or uri == "":
                    continue
                file = in_set(result_path(uri), root)
                if file is None:
                    continue
                rule_id = result.get("ruleId")
                rule_id = rule_id if isinstance(rule_id, str) else None
                bucket.append({
                    "file": file,
                    "lines": result_lines(physical),
                    "classes": result_classes(tid, result, find_rule(run, rule_id)),
                    "message": result.get("message"),
                    "rule_id": rule_id,
                })
    tools: dict[str, dict] = {}
    for tid, results in per_tool.items():
        found: set[int] = set()
        unmatched: set[tuple] = set()
        for res in results:
            hit = [i for i, d in enumerate(defects) if matches(d, res)]
            if hit:
                found.update(hit)
            else:
                lines = res["lines"]
                unmatched.add((res["rule_id"] is not None, res["rule_id"], res["file"],
                               lines[0] if lines else None, lines[1] if lines else None))
        tp = len(found)
        fn = len(defects) - tp
        fp = len(unmatched)
        tools[tid] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": score(tp, tp + fp),
            "recall": score(tp, tp + fn),
            "f1": score(2 * tp, 2 * tp + fp + fn),
        }
    return {"set": root, "defects": len(defects), "tools": tools}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="per-tool confusion matrix of SARIF against labels (CI-SPEC.md P-23)")
    parser.add_argument("--labels", required=True, help="the labels file (P-14)")
    parser.add_argument("sarif", nargs="+", help="SARIF 2.1.0 files")
    args = parser.parse_args(argv)
    with open(args.labels, encoding="utf-8") as fh:
        labels = json.load(fh)
    documents = []
    for path in args.sarif:
        with open(path, encoding="utf-8") as fh:
            documents.append(json.load(fh))
    json.dump(confusion_matrix(labels, documents), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
