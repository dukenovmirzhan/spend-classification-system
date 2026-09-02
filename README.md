# Hierarchical Spend Classification System

**A 12-digit nomenclature taxonomy for multi-site industrial procurement — design, governance rules, and reconciliation method.**

Built for a vertically integrated agro-industrial group operating two production
sites. Published here as methodology and reference implementation on synthetic
data. No proprietary figures, supplier names, or company records are included.

---

## The problem

The group ran procurement across two production sites on a shared ERP, but
without a shared vocabulary for *what* was being bought.

Symptoms:

- The same physical item existed under several different names across sites, so
  demand could not be consolidated and volume leverage was lost.
- Spend could be reported by cost centre and by supplier, but not by **category**
  — which is the only view a category manager can actually act on.
- Category ownership could not be assigned, because there was no stable object
  to own.
- Any question of the form "how much do we spend on this category per year,
  across both sites?" required a manual, non-repeatable data pull.

The root cause was not bad data entry. It was the absence of a classification
layer between raw ERP nomenclature and management reporting.

## Why off-the-shelf classifications did not fit

UNSPSC, eCl@ss and CPV were evaluated first. They were rejected for this case:

- They are designed for cross-company interoperability, not internal category
  management, and their category boundaries do not align with how procurement
  responsibility is actually split here.
- Coverage of local industrial and MRO nomenclature is uneven.
- Mapping legacy items into them required as much manual work as building a
  purpose-designed scheme, without producing a structure anyone in the
  organisation could navigate unaided.

The decision was to design an internal taxonomy, with the explicit trade-off:
better internal fit, no external interoperability. For an organisation whose
spend data is not exchanged with outside parties, this is the right trade.

## Design

The code is a fixed-length, 12-digit, strictly hierarchical identifier. Each
level narrows the one above it; no level can be interpreted on its own. Level 1
is the category — eight in total — and is the unit to which ownership is
assigned.

The 12 digits split across four levels, 2-2-4-4:

```
99  99  9999  9999
│   │   │     └──── item and its characteristics (variant, size, grade, execution)
│   │   └────────── parent nomenclature — the item group (e.g. bearing)
│   └────────────── sub-category
└────────────────── category (8 in use)
```

Illustrative code on synthetic data:

```
03 07 0142 0031
│  │  │    └── deep groove ball bearing, 6208-2RS
│  │  └─────── bearings
│  └────────── rotating equipment components
└───────────── MRO and spare parts
```

Capacity was sized deliberately rather than fitted to the current volume: 99
categories against 8 in use, 99 sub-categories per category, and 9,999 groups
and 9,999 items per branch. The two upper levels are narrow because they encode
management structure, which changes slowly; the two lower levels are wide because
nomenclature grows continuously and must never force a renumbering above it.

Design constraints that drove the structure:

1. **Fixed length.** Variable-length codes break sorting, joins and spreadsheet
   handling. Every code is exactly 12 digits.
2. **Numeric only.** The scheme has to survive being pasted into 1C, Excel and
   Power BI without encoding surprises.
3. **Mutually exclusive branches.** Every item resolves to exactly one leaf. If
   two branches can both accept an item, the branch definition is wrong — not the
   classifier's judgement.
4. **Spare capacity at every level.** Ranges are deliberately left unassigned so
   new sub-categories can be inserted without renumbering siblings. A taxonomy
   that has to be renumbered is a taxonomy that gets abandoned.
5. **Category ownership maps to level 1.** Eight top-level categories, each with
   a single accountable owner. This was a design goal, not an outcome — the
   taxonomy exists to make ownership assignable.

## Governance rules

A classification scheme without governance decays within one reporting cycle.
The rules shipped with the scheme:

- **Single point of assignment.** New codes are issued centrally. Sites request,
  they do not create.
- **Codes are never reused.** A deprecated code is retired, not recycled — this
  keeps historical reporting stable.
- **Reclassification is versioned.** When an item moves branches, the change is
  logged with an effective date, so prior-period reports remain reproducible.
- **The unclassified bucket is monitored, not hidden.** A residual bucket exists
  by design; the metric that matters is its share of total spend and whether it
  is trending down.

## Reconciliation method

A classification is only trustworthy if it accounts for **all** spend, not the
convenient part. The validation approach:

1. Extract the full transaction set from the ERP for the target period, per site.
2. Establish the control total independently — from the ERP's own financial
   reporting, not from the extract.
3. Map items to codes.
4. Sum classified spend and compare to the control total.
5. **The difference must be zero.** Not "close" — zero. Any residual is
   unclassified spend and is reported as such, by value and by share.

This step is where most classification projects quietly fail: they classify what
maps easily, report a coverage percentage, and never reconcile to the books. Sums
that tie exactly to the ERP control totals are what makes the output usable in a
management discussion rather than an interesting exercise.

Both production sites were reconciled to exact ERP control totals for the 2025
reporting year.

## What is in this repository

```
/schema/taxonomy.csv    the taxonomy itself — code, level, parent, name
/schema/rules.csv       classification rules, ordered by priority
/scripts/               synthetic data generation, classification, reconciliation
/docs/governance.md     code issuance, reclassification log, residual bucket, review cadence
```

The generator reproduces the structure and messiness of real industrial
nomenclature — the same item under several spellings, inconsistent separators,
stray whitespace from manual entry, and a share of free-text rows that no rule
set can classify. It contains no real records.

The taxonomy shipped here is a worked example on the same 2-2-4-4 structure, not
the production scheme.

## Reproducing

Python 3.10 or later. No third-party dependencies — the pipeline runs on the
standard library alone, so it can be dropped into a restricted environment
without a package install.

```bash
python scripts/generate_synthetic.py --items 5000 --sites 2
python scripts/classify.py --input synthetic/items.csv --schema schema/
python scripts/reconcile.py --classified out/classified.csv --control synthetic/control_totals.csv
```

`classify.py` validates the taxonomy before it classifies anything: code lengths
must match their level, every code must extend its declared parent, and no parent
may be missing. A malformed schema stops the run rather than producing plausible
output.

`reconcile.py` exits non-zero if classified spend does not tie exactly to the
control totals — the check is designed to fail loudly rather than warn quietly.

## Outcome

- Consolidated category-level spend view across both production sites, produced
  for the first time.
- Category ownership assignable to a defined object, enabling category management
  as a function rather than as a set of ad-hoc sourcing events.
- Repeatable pipeline: subsequent periods are re-run, not rebuilt.
- Data governance implications presented at executive level.

## Limitations and what I would do differently

- **No external interoperability.** Deliberate, but it means supplier-side or
  benchmark data cannot be joined without a mapping layer. If cross-company
  benchmarking ever becomes a requirement, a UNSPSC crosswalk will have to be
  built retrospectively — cheaper to do at design time than later.
- **Classification is still partly manual.** Rule-based matching handles the
  regular cases; the long tail needs a human. An LLM-assisted classification pass
  for the residual bucket is the obvious next step and is not yet implemented.
- **Uniform depth across categories.** The same level depth is applied
  everywhere, and in some categories the deepest level is populated
  inconsistently. A per-category depth policy would have been the better design.

## Author

Mirzhan Dukenov — procurement and supply chain, process design and automation.
[LinkedIn](https://www.linkedin.com/in/mirzhan-dukenov/)

---

*Built during employment. Published as methodology with synthetic data; no
proprietary figures, records, or counterparty information are included.*
