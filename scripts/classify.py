"""Assign 12-digit taxonomy codes to raw ERP nomenclature.

Matching is rule-based and ordered by priority: exact article-number patterns
first, then descriptive phrases, then single generic words. The ordering matters
more than the rules themselves — a generic rule that fires before a specific one
silently misclassifies the item it should have refined.

Anything no rule matches is assigned the residual code and is reported, not
dropped. Coverage that is achieved by discarding awkward rows is not coverage.

Usage:
    python scripts/classify.py --input synthetic/items.csv --schema schema/
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

RESIDUAL_CODE = "999999999999"
RESIDUAL_NAME = "Unclassified"


def load_taxonomy(schema_dir: Path) -> dict[str, dict[str, str]]:
    taxonomy: dict[str, dict[str, str]] = {}
    with (schema_dir / "taxonomy.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            taxonomy[row["code"]] = row
    return taxonomy


def load_rules(schema_dir: Path) -> list[tuple[int, re.Pattern[str], str]]:
    rules: list[tuple[int, re.Pattern[str], str]] = []
    with (schema_dir / "rules.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rules.append((int(row["priority"]), re.compile(row["pattern"], re.I), row["code"]))
    rules.sort(key=lambda r: r[0])
    return rules


def normalise(name: str) -> str:
    """Collapse the noise that manual entry introduces, without losing digits."""
    name = name.strip().lower()
    name = re.sub(r"[*x×]", "x", name)
    name = re.sub(r"\s+", " ", name)
    return name


def classify(name: str, rules: list[tuple[int, re.Pattern[str], str]]) -> str:
    target = normalise(name)
    for _, pattern, code in rules:
        if pattern.search(target):
            return code
    return RESIDUAL_CODE


def validate_schema(taxonomy: dict[str, dict[str, str]]) -> list[str]:
    """Structural checks that must hold for the taxonomy to be usable."""
    problems: list[str] = []
    expected = {"1": 2, "2": 4, "3": 8, "4": 12}
    for code, row in taxonomy.items():
        level = row["level"]
        if len(code) != expected[level]:
            problems.append(f"{code}: length {len(code)} does not match level {level}")
        parent = row["parent"]
        if level != "1":
            if not parent:
                problems.append(f"{code}: level {level} has no parent")
            elif parent not in taxonomy:
                problems.append(f"{code}: parent {parent} not in taxonomy")
            elif not code.startswith(parent):
                problems.append(f"{code}: code does not extend parent {parent}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("out/classified.csv"))
    args = parser.parse_args()

    taxonomy = load_taxonomy(args.schema)
    problems = validate_schema(taxonomy)
    if problems:
        print("taxonomy validation failed:")
        for p in problems:
            print(f"  {p}")
        raise SystemExit(2)

    rules = load_rules(args.schema)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    classified = 0
    residual = 0
    residual_amount = 0.0
    total_amount = 0.0

    with args.input.open(encoding="utf-8") as fin, \
            args.output.open("w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(
            fout,
            fieldnames=list(reader.fieldnames or []) + ["code", "category", "item_name"],
        )
        writer.writeheader()

        for row in reader:
            code = classify(row["raw_name"], rules)
            amount = float(row["amount"])
            total_amount += amount

            if code == RESIDUAL_CODE:
                residual += 1
                residual_amount += amount
                row["category"] = RESIDUAL_NAME
                row["item_name"] = RESIDUAL_NAME
            else:
                classified += 1
                row["category"] = taxonomy[code[:2]]["name"]
                row["item_name"] = taxonomy[code]["name"]

            row["code"] = code
            writer.writerow(row)

    share = residual_amount / total_amount * 100 if total_amount else 0.0
    print(f"classified {classified} rows, residual {residual} rows")
    print(f"residual share of spend: {share:.2f}%")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
