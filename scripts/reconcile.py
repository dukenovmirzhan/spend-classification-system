"""Reconcile classified spend against ERP control totals, per site.

The rule this script enforces: classified spend plus residual spend must equal
the control total exactly. Not approximately. A classification that covers 97%
of spend and cannot say what the other 3% is has not been reconciled, and its
category totals cannot be taken to a management discussion.

The script exits non-zero on any break, so it fails loudly in a pipeline instead
of printing a warning nobody reads.

Usage:
    python scripts/reconcile.py --classified out/classified.csv \\
                                --control synthetic/control_totals.csv
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

RESIDUAL_CODE = "999999999999"
TOLERANCE = Decimal("0.01")  # one currency unit, to absorb rounding only


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classified", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    args = parser.parse_args()

    mapped: dict[str, Decimal] = defaultdict(Decimal)
    residual: dict[str, Decimal] = defaultdict(Decimal)

    with args.classified.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            amount = Decimal(row["amount"])
            if row["code"] == RESIDUAL_CODE:
                residual[row["site"]] += amount
            else:
                mapped[row["site"]] += amount

    control: dict[str, Decimal] = {}
    with args.control.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            control[row["site"]] = Decimal(row["control_total"])

    breaks = 0
    print(f"{'site':<10}{'control':>22}{'classified':>22}{'residual':>20}{'diff':>12}")
    print("-" * 86)

    for site in sorted(control):
        ctrl = control[site]
        mapped_amt = mapped.get(site, Decimal(0))
        residual_amt = residual.get(site, Decimal(0))
        diff = ctrl - (mapped_amt + residual_amt)
        if abs(diff) > TOLERANCE:
            breaks += 1
        print(f"{site:<10}{ctrl:>22,.2f}{mapped_amt:>22,.2f}"
              f"{residual_amt:>20,.2f}{diff:>12,.2f}")

    missing = set(mapped) | set(residual) - set(control)
    missing -= set(control)
    for site in sorted(missing):
        breaks += 1
        print(f"{site:<10}{'no control total':>18}")

    print("-" * 86)

    total_control = sum(control.values())
    total_residual = sum(residual.values())
    if total_control:
        share = total_residual / total_control * 100
        print(f"residual share of total spend: {share:.2f}%")

    if breaks:
        print(f"\nRECONCILIATION FAILED: {breaks} site(s) do not tie to control totals")
        raise SystemExit(1)

    print("\nreconciled: all sites tie to control totals")


if __name__ == "__main__":
    main()
