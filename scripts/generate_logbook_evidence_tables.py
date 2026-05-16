#!/usr/bin/env python3
"""Export rough evidence tables from financial_model.json as PNGs for the business logbook."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.table import Table


def _save_sketch_flow_png(out: Path) -> None:
    """Informal workflow diagram for the logbook evidence annex (no xkcd fonts required)."""
    fig, ax = plt.subplots(figsize=(9.5, 3.2))
    fig.patch.set_facecolor("#f7f8fb")
    ax.set_facecolor("#f7f8fb")
    ax.axis("off")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    boxes: list[tuple[float, float, str]] = [
        (1.4, 1.5, "Sources\nand meetings"),
        (5.0, 1.5, "Python\nmodel"),
        (8.8, 1.5, "LaTeX\nand slides"),
    ]
    for x, y, label in boxes:
        patch = FancyBboxPatch(
            (x - 1.0, y - 0.55),
            2.0,
            1.1,
            boxstyle="round,pad=0.02,rounding_size=0.15",
            linewidth=1.8,
            linestyle="--",
            edgecolor="#3d4f66",
            facecolor="#ffffff",
        )
        ax.add_patch(patch)
        ax.text(x, y, label, ha="center", va="center", fontsize=11, color="#111111")
    ax.annotate(
        "",
        xy=(3.6, 1.5),
        xytext=(2.4, 1.5),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#333333", "linestyle": ":"},
    )
    ax.annotate(
        "",
        xy=(7.2, 1.5),
        xytext=(6.0, 1.5),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#333333", "linestyle": ":"},
    )
    ax.set_title("Workflow: evidence and inputs to model, outputs, and deliverables", fontsize=12.5, pad=10, color="#1e2430", fontweight="semibold")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def _save_table_png(title: str, headers: list[str], rows: list[list[str]], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, min(2.2 + 0.35 * len(rows), 14)))
    fig.patch.set_facecolor("#f7f8fb")
    ax.axis("off")
    ax.set_facecolor("#f7f8fb")
    ax.set_title(title, fontsize=11.5, fontweight="bold", pad=14, color="#1e2430")
    table: Table = ax.table(
        cellText=rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.2)
    table.scale(1.06, 1.38)
    header_bg = "#2f3b52"
    row_a = "#ffffff"
    row_b = "#eef1f7"
    edge = "#cfd8e6"
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(edge)
        cell.set_linewidth(0.65)
        txt = cell.get_text()
        if row == 0:
            cell.set_facecolor(header_bg)
            txt.set_color("#f4f6fb")
            txt.set_fontweight("bold")
            txt.set_fontsize(8.4)
        else:
            cell.set_facecolor(row_b if row % 2 == 0 else row_a)
            txt.set_color("#22262e")
            txt.set_fontsize(8.1)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    data_path = root / "latex" / "HarryEmes" / "Business" / "financial_model.json"
    out_dir = root / "figures" / "logbook_evidence"
    if not data_path.is_file():
        print(f"Missing {data_path}", file=sys.stderr)
        return 1

    data = json.loads(data_path.read_text(encoding="utf-8"))

    rev = data["revenue_schedule"]
    yk = rev["Year"]
    rate_key = next(k for k in rev if "Blended" in k)
    rev_k_key = next(k for k in rev if "Revenue" in k)
    rev_rows = []
    for i, y in enumerate(rev["Year"]):
        rev_rows.append(
            [
                str(y),
                str(rev["Test days sold"][i]),
                str(rev["Fleet size"][i]),
                f"£{rev[rate_key][i]:,}",
                f"£{rev[rev_k_key][i]:.0f}k",
            ]
        )
    _save_table_png(
        "Revenue schedule (exported from driver JSON)",
        ["Year", "Days sold", "Fleet", "Blended £/day", "Revenue"],
        rev_rows,
        out_dir / "table_revenue_schedule.png",
    )

    capex = data["capex_schedule"]
    veh_k = next(k for k in capex if "Vehicle capex" in k)
    setup_k = next(k for k in capex if "Other setup" in k or "setup" in k.lower())
    tot_k = next(k for k in capex if "Total capex" in k)
    capex_rows = []
    for i, y in enumerate(capex["Year"]):
        capex_rows.append(
            [
                str(y),
                str(int(capex["New vehicles purchased"][i])),
                f"£{capex[veh_k][i]:.0f}k",
                f"£{capex[setup_k][i]:.0f}k",
                f"£{capex[tot_k][i]:.0f}k",
            ]
        )
    _save_table_png(
        "CAPEX schedule (exported from driver JSON)",
        ["Year", "New vehicles", "Vehicle capex", "Setup", "Total capex"],
        capex_rows,
        out_dir / "table_capex_schedule.png",
    )

    pnl = data["pnl"]
    py = pnl["Year"]
    rev_k = next(k for k in pnl if k.startswith("Revenue"))
    ebitda_k = next(k for k in pnl if "EBITDA" in k)
    ebit_k = next(k for k in pnl if k.startswith("EBIT") and "EBITDA" not in k)
    np_k = next(k for k in pnl if "Net profit" in k)
    pnl_rows = []
    for i, y in enumerate(pnl["Year"]):
        pnl_rows.append(
            [
                str(y),
                f"£{pnl[rev_k][i]:.0f}k",
                f"£{pnl[ebitda_k][i]:.0f}k",
                f"£{pnl[ebit_k][i]:.0f}k",
                f"£{pnl[np_k][i]:.0f}k",
            ]
        )
    _save_table_png(
        "Five-year P&L summary (exported from driver JSON)",
        ["Year", "Revenue", "EBITDA", "EBIT", "Net profit"],
        pnl_rows,
        out_dir / "table_pnl_summary.png",
    )

    sens = data["sensitivity"]
    low_k = next(k for k in sens if k.startswith("Low EBIT"))
    base_k = next(k for k in sens if k.startswith("Base EBIT"))
    high_k = next(k for k in sens if k.startswith("High EBIT"))
    swing_k = next(k for k in sens if "Swing" in k)
    sens_rows = []
    for i, d in enumerate(sens["Driver"]):
        sens_rows.append(
            [
                d,
                sens["Perturbation"][i],
                f"£{sens[low_k][i]:.0f}k",
                f"£{sens[base_k][i]:.0f}k",
                f"£{sens[high_k][i]:.0f}k",
                f"£{sens[swing_k][i]:.0f}k",
            ]
        )
    _save_table_png(
        "Tornado drivers vs Y3 EBIT (exported from driver JSON)",
        ["Driver", "Shock", "Low EBIT", "Base", "High EBIT", "Swing"],
        sens_rows,
        out_dir / "table_sensitivity_y3_ebit.png",
    )

    _save_sketch_flow_png(out_dir / "sketch_evidence_to_chapter.png")

    print(f"Wrote PNG tables under {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
