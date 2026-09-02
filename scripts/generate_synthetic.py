"""Generate a synthetic procurement transaction set.

The point of this generator is not to produce clean data. Real ERP nomenclature
is inconsistent: the same item appears under several spellings, units drift,
abbreviations are entered by hand. The generator reproduces that noise so the
classification and reconciliation steps are exercised against something that
behaves like a real extract.

Nothing here is derived from a real company's records.

Usage:
    python scripts/generate_synthetic.py --items 5000 --sites 2
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

# Canonical item names paired with the messy variants seen in real extracts.
CATALOGUE: list[tuple[str, list[str], str, tuple[int, int]]] = [
    ("Deep groove ball bearing 6208-2RS",
     ["bearing 6208 2RS", "BALL BEARING 6208-2RS", "brg 6208 2rs", "Bearing  6208-2rs SKF"],
     "pcs", (15_000, 45_000)),
    ("Deep groove ball bearing 6308-2RS",
     ["bearing 6308-2RS", "ball bearing 6308 2rs", "BRG 6308-2RS"],
     "pcs", (20_000, 60_000)),
    ("Tapered roller bearing 32210",
     ["roller bearing 32210", "bearing 32210", "TAPERED BRG 32210"],
     "pcs", (25_000, 70_000)),
    ("Oil seal 40x62x8 NBR",
     ["oil seal 40-62-8", "seal 40x62x8 NBR", "OIL SEAL 40*62*8"],
     "pcs", (2_000, 6_000)),
    ("V-belt SPZ 1250",
     ["v belt SPZ-1250", "V-BELT SPZ1250", "belt spz 1250"],
     "pcs", (5_000, 12_000)),
    ("Hex bolt M12x60 8.8 zinc",
     ["hex bolt M12x60", "bolt M12*60 8.8", "BOLT M12-60 ZINC"],
     "pcs", (150, 400)),
    ("Hex nut M12 8.8 zinc",
     ["hex nut M12", "nut M12 8.8", "NUT M12 ZINC"],
     "pcs", (80, 200)),
    ("Power cable 3x2.5 mm2",
     ["cable 3x2.5", "power cable 3*2.5 mm2", "CABLE 3X2.5MM2"],
     "m", (900, 2_200)),
    ("Contactor 25A 230V",
     ["contactor 25A", "CONTACTOR 25 A 230V", "contactor 25a 230 v"],
     "pcs", (18_000, 40_000)),
    ("Pneumatic cylinder 32x100",
     ["pneumatic cylinder 32-100", "PNEUM CYLINDER 32x100", "cylinder 32*100"],
     "pcs", (35_000, 80_000)),
    ("Hydraulic hose DN12 2SN",
     ["hydraulic hose DN12", "HOSE DN12 2SN", "hose dn 12 2sn"],
     "m", (4_000, 9_000)),
    ("Feed wheat bulk",
     ["feed wheat", "FEED WHEAT BULK", "wheat feed grade"],
     "t", (95_000, 130_000)),
    ("Soybean meal 46% protein",
     ["soybean meal 46", "SOYBEAN MEAL 46%", "soya meal 46 protein"],
     "t", (210_000, 280_000)),
    ("PP tray 187x137x40",
     ["pp tray 187-137-40", "PP TRAY 187X137X40", "tray pp 187*137*40"],
     "pcs", (35, 70)),
    ("Barrier film 60 mic",
     ["barrier film 60mic", "FILM BARRIER 60 MIC", "film 60 mic barrier"],
     "kg", (2_500, 5_000)),
    ("Corrugated box 400x300x200",
     ["corrugated box 400-300-200", "BOX 400X300X200", "box corrugated 400*300*200"],
     "pcs", (200, 450)),
    ("Spiral freezer line",
     ["spiral freezer", "SPIRAL FREEZER LINE", "freezer spiral line"],
     "pcs", (40_000_000, 90_000_000)),
    ("Modular belt conveyor",
     ["belt conveyor modular", "MODULAR BELT CONVEYOR", "conveyor modular belt"],
     "pcs", (1_500_000, 4_000_000)),
    ("Pump overhaul service",
     ["pump overhaul", "PUMP OVERHAUL SERVICE", "overhaul of pump"],
     "svc", (300_000, 900_000)),
    ("Scale calibration service",
     ["scale calibration", "SCALE CALIBRATION SERVICE", "calibration of scales"],
     "svc", (60_000, 150_000)),
    ("Electricity supply",
     ["electricity supply", "ELECTRICITY SUPPLY", "electricity"],
     "kWh", (30, 60)),
    ("Diesel fuel bulk",
     ["diesel fuel", "DIESEL FUEL BULK", "diesel"],
     "l", (280, 340)),
    ("Gear oil ISO VG 220",
     ["gear oil VG 220", "GEAR OIL ISO VG220", "lubricant gear oil vg 220"],
     "l", (2_800, 4_500)),
    ("Refrigerated road transport",
     ["refrigerated transport", "REFRIGERATED ROAD TRANSPORT", "transport refrigerated"],
     "trip", (180_000, 420_000)),
    ("Third-party cold storage",
     ["cold storage", "COLD STORAGE 3PL", "storage cold third party"],
     "t-day", (1_200, 3_000)),
    ("A4 paper",
     ["a4 paper", "A4 PAPER 80G", "paper a4"],
     "pack", (1_400, 2_200)),
    ("Office software licence",
     ["software licence", "SOFTWARE LICENCE OFFICE", "licence software"],
     "pcs", (25_000, 60_000)),
]

# A share of rows is deliberately left unmappable: free-text one-off purchases
# that no rule set will catch. A residual bucket is a fact of life; the pipeline
# must report it rather than hide it.
UNMAPPABLE = [
    "misc purchase per request 114-B",
    "one-off order, see attachment",
    "spare part (no article), urgent",
    "material per memo 22/7",
    "consumables assorted",
]


def noisy(name: str, rng: random.Random) -> str:
    """Apply the kind of damage manual data entry actually does."""
    if rng.random() < 0.10:
        name = name.replace(" ", "  ")
    if rng.random() < 0.08:
        name = " " + name
    if rng.random() < 0.08:
        name = name + " "
    return name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=int, default=5000, help="number of transactions")
    parser.add_argument("--sites", type=int, default=2, help="number of production sites")
    parser.add_argument("--unmapped-share", type=float, default=0.04,
                        help="share of rows that no rule can classify")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    parser.add_argument("--outdir", type=Path, default=Path("synthetic"))
    args = parser.parse_args()

    rng = random.Random(args.seed)
    args.outdir.mkdir(parents=True, exist_ok=True)

    sites = [f"SITE-{i + 1}" for i in range(args.sites)]
    rows = []

    for n in range(args.items):
        site = rng.choice(sites)
        if rng.random() < args.unmapped_share:
            raw_name, unit, price = rng.choice(UNMAPPABLE), "pcs", rng.uniform(500, 90_000)
        else:
            _, variants, unit, (lo, hi) = rng.choice(CATALOGUE)
            raw_name, price = rng.choice(variants), rng.uniform(lo, hi)

        qty = rng.randint(1, 40)
        amount = round(price * qty, 2)
        rows.append({
            "transaction_id": f"TR{n + 1:07d}",
            "site": site,
            "raw_name": noisy(raw_name, rng),
            "unit": unit,
            "quantity": qty,
            "amount": amount,
        })

    items_path = args.outdir / "items.csv"
    with items_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Control totals are written independently of the classification step, the
    # way they would be taken from ERP financial reporting rather than from the
    # extract being classified.
    totals: dict[str, float] = {s: 0.0 for s in sites}
    for r in rows:
        totals[r["site"]] += r["amount"]

    control_path = args.outdir / "control_totals.csv"
    with control_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["site", "control_total"])
        for site in sites:
            writer.writerow([site, round(totals[site], 2)])

    print(f"wrote {len(rows)} transactions to {items_path}")
    print(f"wrote control totals for {len(sites)} sites to {control_path}")


if __name__ == "__main__":
    main()
