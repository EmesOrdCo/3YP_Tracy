#!/usr/bin/env python3
"""Expand HarryEmes/Business/harry_business_body.tex + tables into
latex/CombinedFinal/main_single_file.tex between the harry_business_body
INLINE markers. Run after editing harry_business_body.tex or any
HarryEmes/Business/tables/*.tex so the combined build matches."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUSINESS = ROOT.parent / "HarryEmes" / "Business"
BODY = BUSINESS / "harry_business_body.tex"
MAIN = ROOT / "main_single_file.tex"


def expand_table_inputs(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        rel = m.group(1)
        tbl_path = BUSINESS / rel
        if not tbl_path.is_file():
            raise FileNotFoundError(tbl_path)
        tbl = tbl_path.read_text().rstrip("\n") + "\n"
        marker = f"HarryEmes/Business/{rel}"
        return (
            f"% --- BEGIN INLINE: {marker} ---\n"
            f"{tbl}"
            f"% --- END INLINE: {marker} ---"
        )

    # Consume one newline after each \input so we do not accumulate blanks.
    return re.sub(
        r"\\input\{(tables/[^}]+)\}\s*\n",
        lambda m: repl(m) + "\n",
        text,
    )


def main() -> int:
    body = BODY.read_text()
    expanded = expand_table_inputs(body)

    main_tex = MAIN.read_text()
    pat = re.compile(
        r"(% --- BEGIN INLINE: HarryEmes/Business/harry_business_body\.tex ---\n)"
        r".*?"
        r"(\n% --- END INLINE: HarryEmes/Business/harry_business_body\.tex ---)",
        re.DOTALL,
    )

    def repl_fn(m: re.Match[str]) -> str:
        return m.group(1) + expanded.rstrip() + m.group(2)

    new_main, n = pat.subn(repl_fn, main_tex, count=1)
    if n != 1:
        print("error: harry_business_body INLINE block not found exactly once", file=sys.stderr)
        return 1

    if new_main == main_tex:
        print("main_single_file.tex: already in sync")
        return 0

    MAIN.write_text(new_main)
    print("updated", MAIN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
