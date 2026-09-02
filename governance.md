# Governance

A classification scheme is not a deliverable, it is a standing process. Without
the rules below, a taxonomy degrades within one or two reporting cycles: sites
begin creating their own codes, the same item ends up in two branches, and the
category totals stop being comparable period over period.

## Code issuance

New codes are issued centrally. Production sites raise a request; they do not
create codes themselves.

A request must state the item, the intended parent group, and why an existing
code does not fit. The last part is the one that does the work — most requests
are resolved by pointing at a code the requester did not find, not by issuing a
new one.

Issuance rules:

- A new code is created only at level 4 unless a genuinely new group, sub-category
  or category is required.
- Codes are assigned sequentially within the parent, with gaps left deliberately.
- A code is never reused. When an item is retired, its code is marked deprecated
  and stays in the taxonomy so that historical reporting remains stable.

## Reclassification

An item occasionally sits in the wrong branch and must be moved. This is a
controlled change, not an edit.

Each reclassification is recorded with:

| Field | Meaning |
|---|---|
| `date` | when the change was approved |
| `old_code` | the code before the change |
| `new_code` | the code after the change |
| `effective_from` | the period from which the new code applies |
| `reason` | why the item was misplaced |
| `approved_by` | who authorised it |

`effective_from` is the field that matters. Without it, moving an item silently
rewrites prior-period reports, and two people running the same report in
different months get different numbers. With it, historical reports remain
reproducible and the change is visible.

## The residual bucket

Some spend will not classify: one-off purchases, free-text entries, items bought
before the scheme existed. The residual bucket exists by design.

Two rules apply to it:

- It is reported, never hidden. Every reconciliation states residual spend by
  value and as a share of the total.
- It is monitored as a trend. A residual bucket that stays flat means the rule
  set has stopped keeping up with the nomenclature.

A rising residual share is the earliest signal that the taxonomy is decaying, and
it is visible long before category totals start to look wrong.

## Review cadence

- **Monthly** — review the residual bucket, extend rules for recurring entries.
- **Quarterly** — review new codes issued, check for duplicates across branches.
- **Annually** — review the category level against how procurement responsibility
  is actually split. Category structure should follow the operating model; when
  the operating model changes and the taxonomy does not, ownership stops matching
  the data.
