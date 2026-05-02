# Combined engineering report

Single PDF with one table of contents, four author blocks in order (Toby, Yuze, Paul, Harry), and a **biblatex `refsection` per author** so each **References** list appears after that author’s chapter.

## Build

From this directory:

```bash
latexmk -pdf -interaction=nonstopmode -outdir=out main.tex
```

Output: `out/main.pdf` (and auxiliary files under `out/`).

Requires the same TeX stack as the rest of this repo (packages pulled in by `latex/styling.sty`, including **biblatex/biber**, **enumitem**, **titlesec**, **tocloft**, **multirow**, etc.). TeX Live **basic** often lacks packages—install without sudo:

```bash
tlmgr init-usertree   # once per account
tlmgr --usermode install enumitem titlesec tocloft multirow
```

Or use a full TeX Live scheme.

## Layout notes

- Yuze’s folder name contains a space; this folder uses **symlinks** (`yuze_body.tex`, `yuze_references.bib`, `yuze_assets`) so `\input` and `\graphicspath` stay robust.

## Standalone chapters

Each author’s `Engineering/main.tex` still builds alone via `\input{*_body.tex}` next to the shared `*_body.tex` file.
