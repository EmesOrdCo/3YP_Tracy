# Harry Emes — Engineering Report (Simulation chapter)

Working directory for the simulation chapter of the group 3YP report.

## Build

From this directory:

```bash
pdflatex main
biber main
pdflatex main
pdflatex main
```

`latexmk` works too:

```bash
latexmk -pdf main
```

## Files

- `main.tex` — chapter source. Full section/subsection skeleton with equations, figure/table stubs, and `[PLACEHOLDER]` / `[PH]` markers where prose or numbers still need to be filled in.
- `references.bib` — seeded bibliography (numeric/Vancouver, matches `../../styling.sty`).
- `figures/` — chapter-local figures. `\graphicspath{}` in `main.tex` also falls back to the repo-root `figures/` folder, so drafts can pull existing simulation plots without copying.

## Conventions (matches `../../styling.sty`)

- 11 pt, A4, double-spaced, 20 mm margins, Helvetica sans-serif, left-justified.
- Numeric references in square brackets, heading named "References" (not "Bibliography").
- Table captions above, figure captions below.
- Section/subsection depth limited to 3 levels.

## Section map

| # | Section | Target pages |
|---|---------|--------------|
| 1 | Introduction and Scope | 1.0 |
| 2 | Simulation Methodology | 4.5 |
| 3 | Verification and Validation | 2.0 |
| 4 | Parameter Sensitivity and Design Space | 2.5 |
| 5 | Predicted Performance of the Final Vehicle | 2.5 |
| 6 | Discussion and Limitations | 1.0 |
| 7 | Conclusions and Further Work | 0.5 |
|   | References | 1.0 |
|   | **Total** | **~15.0** |

## Placeholder convention

- `[PLACEHOLDER: …]` — a paragraph of prose still to be written, with guidance on what it should contain.
- `[PH]` — a single number, percentage, status string, or short value still to be filled in.
- `%TODO:` — a LaTeX comment flagging work still to do. Strip all of these before submission.

## Pre-submission checklist

- [ ] No `[PLACEHOLDER`, `[PH]`, or `%TODO:` markers remain.
- [ ] Third-person / passive voice throughout (no "I", "we", "my").
- [ ] Every numerical claim either derived, cited, or validated.
- [ ] Rule numbers (FS-EV 2.2, FS-D 5.3.1, FS-D 5.3.2) quoted inline at constraints.
- [ ] Every figure caption carries a one-sentence take-away.
- [ ] Interim conclusions present at the end of §§3, 4, 5.
- [ ] Final Conclusions draws only from §§3–6 and closes with explicit further work.
- [ ] Page count ≤ 15 (including figures, tables, references).
- [ ] Declaration of Authorship page signed and included (not counted).
