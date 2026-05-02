"""Re-render figures with the slide background colour baked in.

Outputs grey-tinted variants of the engineering chapter figures into
``Presentation/figures/`` so they merge seamlessly with the slide canvas
(no floating white rectangles on grey).
"""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

SLIDE_BG = "#E8E8E8"
HERE = Path(__file__).resolve().parent
ENG = HERE.parent / "Engineering"
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

# Slide-readable typography for any matplotlib figure routed through here.
SLIDE_RC = {
    "font.size":        18,
    "axes.titlesize":   20,
    "axes.labelsize":   18,
    "xtick.labelsize":  16,
    "ytick.labelsize":  16,
    "legend.fontsize":  16,
}


# --------------------------------------------------------------------------
# Helper: monkey-patch ``Figure.savefig`` so that any script we re-run will
# (a) tint its figure + axes background to ``SLIDE_BG`` and (b) write the
# file into ``OUT`` instead of the engineering figures folder.
# --------------------------------------------------------------------------

def _bump_text_for_slides(fig):
    """Force all existing text inside ``fig`` up to slide-readable sizes.

    rcParams only affects future text creation; pre-existing artists keep
    whatever ``fontsize`` they were created with. This walks the figure
    after it's been built and bumps anything below the threshold.
    """
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


def _redirect_savefig(name_to_slide_name):
    orig = plt.Figure.savefig

    def patched(self, fname, *args, **kwargs):
        fname = Path(fname)
        if fname.name in name_to_slide_name:
            self.patch.set_facecolor(SLIDE_BG)
            for ax in self.get_axes():
                ax.set_facecolor(SLIDE_BG)
            _bump_text_for_slides(self)
            kwargs["facecolor"] = SLIDE_BG
            kwargs["edgecolor"] = SLIDE_BG
            target = OUT / name_to_slide_name[fname.name]
            return orig(self, target, *args, **kwargs)
        return orig(self, fname, *args, **kwargs)

    plt.Figure.savefig = patched
    return orig


def _restore(orig):
    plt.Figure.savefig = orig


# --------------------------------------------------------------------------
# 1. Schematic + 2. Architecture: re-run their generators redirected to OUT.
# --------------------------------------------------------------------------

def render_schematic_and_architecture():
    redirect_map = {
        "system_overview.pdf": "system_overview.pdf",
        "architecture.pdf":    "architecture.pdf",
    }
    orig = _redirect_savefig(redirect_map)
    try:
        sys.path.insert(0, str(ENG))
        runpy.run_path(str(ENG / "_generate_schematic.py"), run_name="__slide__")
        runpy.run_path(str(ENG / "_generate_architecture.py"), run_name="__slide__")
    finally:
        _restore(orig)
        sys.path.pop(0)


def render_final_run_and_mc():
    """Re-runs the heavy generation scripts but only captures the slide-needed PDFs.

    Slow (~1-3 min) because it re-runs the baseline sim and 500-sample Monte Carlo.
    """
    redirect_map = {
        "final_run.pdf":              "final_run.pdf",
        "final_run_combined.pdf":     "final_run_combined.pdf",
        "mc_histogram.pdf":           "mc_histogram.pdf",
        "optim_convergence.pdf":      "optim_convergence.pdf",
    }
    orig = _redirect_savefig(redirect_map)
    try:
        sys.path.insert(0, str(ENG))
        runpy.run_path(str(ENG / "_generate_report_numbers.py"), run_name="__slide__")
        runpy.run_path(str(ENG / "_generate_extras.py"), run_name="__slide__")
    finally:
        _restore(orig)
        sys.path.pop(0)


# --------------------------------------------------------------------------
# 3. Tornado: replot directly from report_numbers.json with slide bg.
# --------------------------------------------------------------------------

def render_tornado():
    data = json.loads((ENG / "report_numbers.json").read_text())["sensitivity"]
    data = sorted(data, key=lambda r: max(abs(r["dt_low_ms"]), abs(r["dt_high_ms"])))

    labels = [r["label"] for r in data]
    low    = np.array([r["dt_low_ms"]  for r in data])
    high   = np.array([r["dt_high_ms"] for r in data])
    y      = np.arange(len(labels))

    with plt.rc_context(SLIDE_RC):
        fig, ax = plt.subplots(figsize=(9.0, 6.4))
        fig.patch.set_facecolor(SLIDE_BG)
        ax.set_facecolor(SLIDE_BG)

        ax.barh(y, low,  color="#1F4E79", alpha=0.85, label=r"$-10\%$")
        ax.barh(y, high, color="#C0392B", alpha=0.85, label=r"$+10\%$")

        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.set_xlabel("Change in 75 m time vs baseline (ms)", fontsize=22)
        ax.tick_params(axis="y", labelsize=20)
        ax.tick_params(axis="x", labelsize=18)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            ax.spines[spine].set_color("0.4")
        ax.grid(axis="x", alpha=0.25)
        leg = ax.legend(loc="lower right", framealpha=0.92, fancybox=False)
        leg.get_frame().set_facecolor(SLIDE_BG)
        leg.get_frame().set_edgecolor("0.55")

        fig.tight_layout()
        fig.savefig(OUT / "tornado.pdf",
                    bbox_inches="tight", facecolor=SLIDE_BG, edgecolor=SLIDE_BG)
        plt.close(fig)
    print(f"Wrote {OUT / 'tornado.pdf'}")


# --------------------------------------------------------------------------
# 4. GUI screenshot: replace pure-white background pixels with slide grey.
# --------------------------------------------------------------------------

def tint_gui_screenshot():
    src = ENG / "figures" / "gui_optimizer.png"
    dst = OUT / "gui_optimizer.png"
    img = Image.open(src).convert("RGB")
    arr = np.array(img)
    bg = np.array([0xE8, 0xE8, 0xE8], dtype=np.uint8)
    white_mask = (arr[..., 0] >= 245) & (arr[..., 1] >= 245) & (arr[..., 2] >= 245)
    arr[white_mask] = bg
    Image.fromarray(arr).save(dst, optimize=True)
    print(f"Wrote {dst}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true",
                        help="skip the heavy final_run + Monte Carlo regen")
    args = parser.parse_args()

    render_schematic_and_architecture()
    render_tornado()
    tint_gui_screenshot()
    if not args.fast:
        render_final_run_and_mc()
    print("\nAll slide figures regenerated into", OUT)
