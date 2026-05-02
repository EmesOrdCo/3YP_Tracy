"""Re-run only the optimiser portion of _generate_extras.py with the slide
background colour, so we don't have to wait for the 500-sample Monte Carlo.

Uses the same monkey-patch trick as _make_slide_figs.py.
"""

from __future__ import annotations

import os
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


orig_savefig = plt.Figure.savefig

def patched(self, fname, *args, **kwargs):
    fname = Path(fname)
    if fname.name == "optim_convergence.pdf":
        self.patch.set_facecolor(SLIDE_BG)
        for ax in self.get_axes():
            ax.set_facecolor(SLIDE_BG)
        kwargs["facecolor"] = SLIDE_BG
        kwargs["edgecolor"] = SLIDE_BG
        target = OUT / "optim_convergence.pdf"
        return orig_savefig(self, target, *args, **kwargs)
    if fname.name == "mc_histogram.pdf":
        # Skip MC re-run: we already have the slide-bg version
        print("[skip] mc_histogram.pdf already produced")
        return None
    return orig_savefig(self, fname, *args, **kwargs)

plt.Figure.savefig = patched

# Skip the slow 500-sample MC: only need the optimiser trace here.
os.environ["REPORT_N_MC"] = "5"

sys.path.insert(0, str(ENG))
runpy.run_path(str(ENG / "_generate_extras.py"), run_name="__slide_optim__")
