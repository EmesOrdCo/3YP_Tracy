# Combined Final Report (Engineering + Business)

A single PDF with **one** table of contents at the front and two parts:

1. **Part I — Engineering Report:** Toby → Ziyang Xing → Yuze → Paul → Harry
2. **Part II — Business Report:** Toby → Paul → Ziyang Xing → Yuze → Harry

Each author's chapter is wrapped in a biblatex `refsection`, so each one's references list appears at the end of that chapter.

## Build

```bash
cd latex/CombinedFinal
latexmk -pdf -interaction=nonstopmode -outdir=out main.tex
```

Output: `out/main.pdf`.

If TeX Live basic is missing packages, install without sudo:

```bash
tlmgr init-usertree
tlmgr --usermode install enumitem titlesec tocloft multirow xurl
```

## Layout

This folder uses **symlinks** so paths avoid the space in `Yuze Jiang` and so Harry's `\input{tables/...}` resolves:

- `yuze_engineering_body.tex` → `../Yuze Jiang/yuze_body.tex`
- `yuze_business_body.tex`    → `../Yuze Jiang/yuze_business_body.tex`
- `yuze_references.bib`       → `../Yuze Jiang/references.bib`
- `yuze_assets`               → `../Yuze Jiang`
- `tables`                    → `../HarryEmes/Business/tables`

Yuze's `references.bib` is **one file** shared by both his Engineering and Business chapters, so it is added once via biblatex.

Harry's compact-chapter macros are `\input` only just before his Business `refsection`; everything earlier uses standard chapter formatting.
