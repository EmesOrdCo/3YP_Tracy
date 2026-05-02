"""Re-render only ``final_run.pdf`` with the slide background colour.

Runs ``_generate_report_numbers.py`` (which is ~1-2 min) and intercepts
the savefig for the final-run figure only, dropping it into the slide
figures folder with the slide background and bumped fonts.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SLIDE_BG = "#E8E8E8"
HERE = Path(__file__).resolve().parent
ENG = HERE.parent / "Engineering"
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)


def _bump_text_for_slides(fig):
    for ax in fig.get_axes():
        for txt in (ax.title, ax.xaxis.label, ax.yaxis.label):
            if txt.get_fontsize() < 18:
                txt.set_fontsize(18)
        for lbl in ax.get_xticklabels() + ax.get_yticklabels():
            if lbl.get_fontsize() < 14:
                lbl.set_fontsize(14)
        leg = ax.get_legend()
        if leg is not None:
            for t in leg.get_texts():
                if t.get_fontsize() < 14:
                    t.set_fontsize(14)


orig_savefig = plt.Figure.savefig

def patched(self, fname, *args, **kwargs):
    fname = Path(fname)
    if fname.name in ("final_run.pdf", "final_run_combined.pdf"):
        self.patch.set_facecolor(SLIDE_BG)
        for ax in self.get_axes():
            ax.set_facecolor(SLIDE_BG)
        _bump_text_for_slides(self)
        kwargs["facecolor"] = SLIDE_BG
        kwargs["edgecolor"] = SLIDE_BG
        target = OUT / fname.name
        return orig_savefig(self, target, *args, **kwargs)
    # Skip everything else (tornado / dry_wet / dt_convergence)
    print(f"[skip] {fname.name}")
    return None

plt.Figure.savefig = patched

sys.path.insert(0, str(ENG))
runpy.run_path(str(ENG / "_generate_report_numbers.py"), run_name="__final_run__")
