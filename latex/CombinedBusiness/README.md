# Combined business report

Single PDF with one table of contents, four author blocks in order **Toby → Paul → Yuze → Harry**. **Paul, Yuze, and Harry** use **biblatex `refsection`s** so each **References** list appears after that chapter. **Toby’s** block is included **before** the first `refsection` (no citations; avoids a `refsection` + table edge case on this TeX install).

Yuze’s standalone business document is [`Yuze Jiang/EEM.tex`](../Yuze%20Jiang/EEM.tex) (not `Business/main.tex`). The shared body is [`yuze_business_body.tex`](../Yuze%20Jiang/yuze_business_body.tex).

## Build

```bash
cd latex/CombinedBusiness
latexmk -pdf -interaction=nonstopmode -outdir=out main.tex
```

Output: `out/main.pdf`.

TeX Live **basic** may need extra packages; use `tlmgr --usermode install …` (see [`CombinedEngineering/README.md`](../CombinedEngineering/README.md)) or a full TeX scheme.

This folder uses **symlinks** (`yuze_business_body.tex`, `yuze_business_references.bib`, `yuze_assets`, and `tables` → `../HarryEmes/Business/tables`) so paths avoid spaces in `Yuze Jiang` and so Harry’s table fragments under `tables/` resolve when building from this directory.

## Standalone builds

Each author’s Business sources still build alone (Toby/Paul/Harry `Business/main.tex`; Yuze `EEM.tex`) via `\input{*_business_body.tex}`.
