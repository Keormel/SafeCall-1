"""Coverage gates from the test plan. Run after `pytest --cov=app --cov-report=json`.

    python tests/check_coverage.py coverage.json
"""

import json
import sys

CORE = {
    "app/services/risk_engine.py": 95,
    "app/services/campaign_engine.py": 95,
    "app/services/fingerprint.py": 95,
    "app/services/phone.py": 95,
}
TOTAL = 85


def main(path: str) -> int:
    report = json.load(open(path))
    failures = []
    for file, minimum in CORE.items():
        got = report["files"][file]["summary"]["percent_covered"]
        status = "ok" if got >= minimum else "FAIL"
        print(f"{status:4} {file:40} {got:6.2f}% (min {minimum}%)")
        if got < minimum:
            failures.append(file)
    total = report["totals"]["percent_covered"]
    print(f"{'ok' if total >= TOTAL else 'FAIL':4} {'backend total':40} {total:6.2f}% (min {TOTAL}%)")
    if total < TOTAL:
        failures.append("total")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "coverage.json"))
