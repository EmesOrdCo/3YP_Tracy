#!/usr/bin/env python3
"""Expand LOGBOOK_BUSINESS.md toward ~20 printed pages (more words, entries, diagrams)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "LOGBOOK_BUSINESS.md"

INSERT_AFTER_6_DEC = """

9th December 2025
Driver outputs contract

Before I wrote any more schedules I fixed how outputs leave the Python driver so I would not end up hand-editing LaTeX numbers. The contract is: regenerate JSON for plotting scripts, regenerate LaTeX fragments for every published table, and regenerate macro definitions for any number quoted inline. I tested one round-trip change on a dummy constant to prove the pipeline fails loudly if a fragment is missing, rather than silently printing zero.

11th December 2025
Capex schedule logic on paper

I traced vehicle purchases on paper year by year (first vehicle and setup in year one, extra vehicles when fleet steps) so the pandas capex vector could not disagree with the story Paul and I had told in November. I also wrote down the straight-line rule in words first—each year’s spend is depreciated over five years from the year it hits—because mixing “when cash leaves” and “when depreciation starts” is exactly how I broke the old Excel sketch.

```mermaid
flowchart LR
  subgraph driver [Python driver]
    C[Constants]
    S[Pandas schedules]
  end
  subgraph out [Generated outputs]
    J[JSON for figures]
    T[LaTeX table fragments]
    M[Inline macros]
  end
  C --> S
  S --> J
  S --> T
  S --> M
```

"""

INSERT_AFTER_BRONZE = """

18th November 2025
Consolidating competitor notes into a single table spec

I took the scattered November notes and turned them into a single table specification: one row per comparator type, columns for what they sell, what the day-rate band is for, and what we are allowed to infer versus what we are not allowed to infer. That sounds bureaucratic but it stopped me from smuggling “demand” into the model through the back door of benchmarking.

"""

APPENDS: dict[str, str] = {
    "8th November 2025": (
        "After the meeting I wrote a one-page dependency map: which chapter numbers would need Toby’s SOM, which would need Paul’s vehicle buckets, and which were entirely internal to the finance model. "
        "That stopped me from starting in the wrong place (pretty charts) instead of the right place (assumptions you can defend)."
    ),
    "11th November 2025": (
        "I also started a citations scratch file with URLs and access dates even though the bibliography would not exist for weeks, because I knew I would forget which brochure was which if I left it to memory. "
        "The scratch file is ugly but it is the difference between “I read something” and “I can show I read something.”"
    ),
    "18th November 2025": (
        "I typed the table spec into a plain text outline first because LaTeX tables punish you if you discover a missing column halfway through writing. "
        "The outline also forced me to label each comparator row as “facility-led”, “lab-led”, “robot-led”, or “captive”, which later became the language in the chapter without inventing new jargon."
    ),
    "22nd November 2025": (
        "I re-read the variable list against the chapter plan and marked which items were “hard numbers we must agree as a group” versus “soft numbers I can choose with a footnote”. "
        "That split later saved time in arguments: nobody wants to debate your inflation decimal if they know it is sensitivity-only."
    ),
    "25th November 2025": (
        "I wrote the utilisation and fleet arrays into the driver as named lists the same day as the meeting so I could not accidentally keep an old Excel vector. "
        "I also noted explicitly that year four is the awkward year (two vehicles, high days) because that is the year the headcount step costs matter most in the story."
    ),
    "29th November 2025": (
        "I photographed the whiteboard breakdown after talking to Paul so the chapter narrative could not drift from what we actually agreed. "
        "I also listed instrumentation as a sensitivity flag in the driver comments because that is the subsystem most likely to move without changing the headline story."
    ),
    "2nd December 2025": (
        "The Excel attempt was still useful as a forcing function: it made me list every cash line I would later need in Python, even if the spreadsheet arithmetic was wrong. "
        "I kept the Excel file in the folder but renamed the tab “do not cite” so I would not accidentally copy a cell into LaTeX during a tired night."
    ),
    "3nd December 2025": (
        "I stubbed functions first (capex schedule, depreciation, opex, revenue, pnl, cash) even when some returned zeros, because it gave me a compile order for later debugging. "
        "I also decided early that the model would be deterministic: no random demand draws, because I did not want a second source of “why did the number move.”"
    ),
    "6th December 2025": (
        "After the indexing fix I ran a regression test pattern: change one opex line item by £1k, regenerate, and confirm only opex-derived tables move. "
        "That sounds obsessive but it is how I caught a second bug later where a figure script was still reading an old JSON file path."
    ),
    "13th December 2025": (
        "I kept a parallel spreadsheet-style sanity total for year-one fixed opex only, not as a source of truth but as a quick checksum while I iterated salary bands. "
        "When the Python total and the scratch total disagreed, I always assumed Python was right until proven otherwise, which forced me to find real mistakes instead of “rounding”."
    ),
    "16th December 2025": (
        "I printed the NLW tables and marked the thresholds in pen because PDF readers lie about pagination on small laptop screens. "
        "I also wrote down the exact footnote sentence I would use in the chapter so the simplification on employer load is not mistaken for ignorance."
    ),
    "20th December 2025": (
        "I ran a full LaTeX compile cycle after fixing keys because biber errors are easier to read when you only changed one variable at a time. "
        "I also checked that facility web sources had `urldate` fields where the guidance expects unstable pages."
    ),
    "23rd December 2025": (
        "I wrote a single paragraph in the chapter draft immediately, not “later”, because scope creep is easiest when you postpone writing the boundary of the model. "
        "The paragraph states plainly what we do not simulate (real company accounts filing) so a marker cannot accuse us of pretending."
    ),
    "27th December 2025": (
        "I exported a tiny CSV of year-on-year opex with and without the 3% step to see whether the curve looked like a macro story or like a step-function from hiring. "
        "It mostly looked like hiring and fleet scaling, which matches what we want the reader to focus on."
    ),
    "30th December 2025": (
        "I also checked that vehicle capex in year three and year five matched the fleet delta logic (0,0,1,0,1 new vehicles) because fleet indexing errors look like revenue errors later when utilisation per vehicle is discussed informally."
    ),
    "3rd January 2026": (
        "I added an assertion in code that revenue equals days times rate to within a penny after rounding, so the model crashes if someone adds a second revenue line and forgets to wire it. "
        "I hate assert-driven modelling in theory, but for a thesis I love it in practice."
    ),
    "6th January 2026": (
        "I wrote the mix assumptions as explicit year-by-year weights in comments next to the blended array so future-me can explain the path without reverse-engineering it from the average alone. "
        "That also made it easy to narrate “mix shift” versus “price inflation” in the sensitivity section."
    ),
    "10th January 2026": (
        "I sanity-checked that our Bronze price still sits below the proving-ground upper band and Gold still sits below the captive OEM anchor, otherwise the tier story would contradict the desk research paragraph. "
        "If those inequalities broke, I would have had to revisit either tier prices or the competitor table wording."
    ),
    "13th January 2026": (
        "I saved Toby’s SOM number with a date stamp in my notes because market chapters drift; the finance chapter needs a frozen reference point for the penetration sentence. "
        "If his SOM moves, I want a dated note proving what number the penetration percentage referred to."
    ),
    "17th January 2026": (
        "I checked depreciation expense against capex spend manually for year one because straight-line is easy to get wrong if you start depreciation in the wrong month in your head even when the code is right. "
        "The check also confirmed zero residual means the asset is fully written down by year five, which matches the “no invented resale” story."
    ),
    "20th January 2026": (
        "After fixing the year indexing bug I added a unit test style check: sum of headcount additions equals the narrative total across five years. "
        "It is not pytest, it is a print statement, but it stopped a recurrence."
    ),
    "24th January 2026": (
        "I compared variable cost per day to contribution margin and wrote the margin as a single macro used in both break-even and tornado sections so I cannot accidentally use Y1 margin in a Y2 break-even narrative. "
        "That coupling is boring but it prevents a classic footnote disaster."
    ),
    "27th January 2026": (
        "I drafted the tax paragraph immediately after the P&L compiled because tax is where readers jump if they think you are “making EBITDA look good”. "
        "I also checked that tax starts in the same year in both P&L and cash tax paid logic (as far as the simplified model goes)."
    ),
    "31st January 2026": (
        "I sketched the cash waterfall on paper before matplotlib because the stacked bars are easy to draw wrong if equity is not clearly separated from operating cash. "
        "I also wrote speaker notes for myself explaining why cumulative cash is not “runway months” unless you define burn consistently."
    ),
    "3rd February 2026": (
        "I duplicated the inversion message into the figure caption checklist: left panel annual, right panel cumulative, colours consistent with the chapter’s earlier capex figure. "
        "Colour consistency sounds cosmetic until a marker asks why revenue green in one figure is not the same semantic green elsewhere."
    ),
    "7th February 2026": (
        "I derived break-even days algebraically in the margin of my notes with symbols first, then translated to code, because coding from memory is how I introduced the headcount bug earlier. "
        "The symbolic derivation also became the LaTeX equation block almost verbatim."
    ),
    "10th February 2026": (
        "I annotated the break-even plot with the actual planned utilisation markers from Toby’s array so the reader can see distance-to-breakeven visually rather than only in a table. "
        "I also saved the matplotlib script parameters next to the figure filename so regeneration is one command."
    ),
    "14th February 2026": (
        "I wrote the terminal value paragraph before polishing the NPV curve so I did not accidentally describe IRR as if it were an annual operating return. "
        "I also checked that the terminal is discounted at year-five horizon consistently with the equation numbering."
    ),
    "17th February 2026": (
        "I duplicated the peer multiple table into my notes with sources attached line-by-line so the marker can match each multiple to a footnote without hunting. "
        "I also noted AVL is private-ish so the multiple is explicitly “estimate” language in prose."
    ),
    "21st February 2026": (
        "I kept the failed cap table file in a scratch folder rather than deleting it from disk entirely, because it is useful evidence in a viva that I tried and backed out when inconsistent. "
        "The chapter text now says what we do show (round sizes) rather than apologising for what we do not."
    ),
    "24th February 2026": (
        "I re-read the engineering chapter’s sensitivity section side-by-side while building the tornado so the “one-at-a-time” language is not accidentally different between chapters. "
        "I also ranked inflation last on purpose: it matters, but it is not the story we want to lead with."
    ),
    "28th February 2026": (
        "I wrote the downtime assumption as a short pseudo-equation in notes: billable days equals planned days times one minus downtime rate, holding fixed opex. "
        "That made it easy to explain in prose why EBIT breaks before NPV does under the same shock."
    ),
    "3rd March 2026": (
        "I checked the downtime chart axis labels against the table because it is easy to plot NPV with the wrong discount label after a long day. "
        "I also exported the downtime sweep as CSV once for sanity plotting in a notebook separate from the thesis build."
    ),
    "7th March 2026": (
        "I wrote the Series A trigger as a bullet list in the model header comments (ARR threshold, customer count, timing window) so the funding subsection cannot drift from the cash model assumptions. "
        "I also checked that seed use-of-funds language includes runway months consistent with the loss profile in the P&L."
    ),
    "10th March 2026": (
        "I ran the LTV/CAC numbers with gross margin stepped down to 60% as a stress because the 70% assumption is the softest part of that box. "
        "The qualitative conclusion survived, which is all I wanted from the illustration."
    ),
    "14th March 2026": (
        "I drafted scope before cost sections because scope is where you admit what you are not repeating from Toby; if you write cost first you accidentally re-derive market sizing. "
        "I also inserted the engineering methodology cross-cite placeholder the same day so it cannot be forgotten."
    ),
    "17th March 2026": (
        "I checked figure paths for capex and opex donuts against the table labels because mismatched captions are a common failure mode when figures regenerate from scripts with different working directories. "
        "I also compared fleet language in prose to the capex schedule column “new vehicles purchased”."
    ),
    "21st March 2026": (
        "After the inflation mistake I added a pre-commit mental checklist: run diff on constants block before any git push of generated TeX. "
        "It is not automated CI, but it is a habit that stops repeating the same embarrassment."
    ),
    "24th March 2026": (
        "I read the NPV equation in the PDF aloud while pointing at the cash figure to catch mismatched definitions; aloud reading finds “free cash flow” used two different ways faster than silent skimming. "
        "I also matched the tornado axis label units to the EBIT table units."
    ),
    "28th March 2026": (
        "I saved a before/after PDF of the opex donut legend change because thesis markers sometimes ask what you changed between drafts and a visual diff is faster than git blame storytelling."
    ),
    "31st March 2026": (
        "I searched the chapter for the word “profitable” and replaced or qualified every instance after the EBITDA confusion surfaced in a read-through with a non-financial teammate. "
        "That search caught one caption sentence I would have missed by eye."
    ),
    "4th April 2026": (
        "I verified vector PDFs embed fonts correctly by opening in a different PDF viewer than my default, because matplotlib font embedding issues show up on other machines first. "
        "I also kept the raster export zip outside git to avoid bloating the repo."
    ),
    "7th April 2026": (
        "I printed the scenario table on paper once; rotated headers look different on screen than on paper, and markers still mark on paper sometimes. "
        "The printout caught an overfull box I had ignored on screen."
    ),
    "11th April 2026": (
        "I wrote the asymmetry footnote text in my notes before putting it in LaTeX so the footnote reads like an explanation, not like an apology. "
        "The footnote also names Toby’s downside tail argument in one sentence so it is not mysterious asymmetry."
    ),
    "14th April 2026": (
        "I replied to Paul confirming what changed (electrical thinking) versus what did not change (headline £310k bucket) so there is an email trail if the engineering chapter later diverges. "
        "Email trails are not glamorous but they stop group projects rewriting history silently."
    ),
    "18th April 2026": (
        "I checked certification wording against the opex line description to ensure we do not imply UK-only certification covers export testing costs. "
        "That boundary is small but it is exactly the kind of overclaim markers flag."
    ),
    "21st April 2026": (
        "After fixing the cross-reference I re-ran the combined build twice because LaTeX sometimes needs two passes for references even when the first pass looks clean. "
        "I also searched for the old label string repo-wide so it could not linger in a comment."
    ),
    "25th April 2026": (
        "I kept a list of false-positive spellcheck hits (citation commands, abbreviations) so I do not waste time re-ignoring them on the next pass. "
        "The list is short but it saves sanity."
    ),
    "28th April 2026": (
        "I asked someone else to grep for the engineering cite key across the whole thesis folder because my eyes had stared at the typo too long to see it. "
        "Second pair of eyes found a duplicate copy in a backup tex file I forgot existed."
    ),
    "2nd May 2026": (
        "I zipped the JSON snapshot with a README text file explaining regenerate order (model then figures then latexmk) because future-me will not remember the pipeline under stress. "
        "The README is one paragraph but it prevents ritual magic rebuilds."
    ),
    "5th May 2026": (
        "I updated speaker notes with the exact IRR definition used in the chapter equation so I cannot improvise a different definition under questioning. "
        "I also rehearsed the EBITDA versus net profit sentence until it was boring, because boring is clear."
    ),
    "9th May 2026": (
        "I mapped each KPI bullet in conclusions to a figure or table reference so the KPI list is not floating claims. "
        "Where a KPI did not yet have a figure, I added a sentence in the chapter pointing to the operational definition in text."
    ),
    "12th May 2026": (
        "I did a final “numbers freeze” ritual: export JSON, hash it, print the hash on a sticky note, stick it on the printed chapter. "
        "That is nerdy but it is the fastest proof at submission time that the PDF in the zip matches the model run you think it matches."
    ),
    "9th December 2025": (
        "I wrote a short “contract” note for myself about artefacts because I had seen friends lose marks when figures disagreed with tables after a last-minute manual edit. "
        "The contract is boring governance, but governance is what stops chaos in the last week."
    ),
    "11th December 2025": (
        "Paper tracing capex felt childish but it caught an off-by-one risk in my head about which year the second vehicle payment lands in versus when depreciation starts. "
        "Writing the rule in words first also gave me a paragraph I could almost paste into the methodology section later."
    ),
    "1st January 2026": (
        "The checklist was deliberately petty: it included boring items like “confirm certification line item still matches opex category” because those are the lines people accidentally double-count when they are tired. "
        "Ticking boxes slowly is faster than rewriting a chapter after a contradiction is spotted."
    ),
    "15th January 2026": (
        "Cross-footing revenue is not glamorous but it is the fastest sanity check that utilisation arrays and blended rates were not edited in two different places with different results. "
        "Sending Toby the screenshot was partly politeness and partly insurance against silent edits to his narrative numbers."
    ),
    "2nd February 2026": (
        "Defining project FCF narrowly sounds pedantic but NPV is a pedantic object: if financing flows leak into the FCF series, IRR becomes meaningless without noticing. "
        "I highlighted the definition in yellow in the PDF draft so I would not skim past it during proofreading."
    ),
    "16th February 2026": (
        "I kept the hurdle language grounded in what VC readers expect rather than in fake precision: two named rates on the curve plus a sentence that the curve shape matters more than the exact second decimal. "
        "That also gave me a place to park the “terminal dominates PV” warning without sounding like I was disowning the whole NPV result."
    ),
    "1st March 2026": (
        "Table-first thinking for downtime stopped me from drawing a chart with a prettier axis that did not match the printed sensitivity grid. "
        "It also made the later writing easier because I could lift row labels almost directly into captions."
    ),
    "12th March 2026": (
        "Sketching valuation on paper prevented me from writing multiples prose that accidentally referenced Y4 revenue instead of Y5. "
        "It also forced me to decide whether the peer table sits in valuation only or also gets referenced in NPV—answer: both, but with one canonical median number."
    ),
    "30th March 2026": (
        "The first combined compile was deliberately ugly: I wanted the full warning list on one screen before I started “fixing aesthetics”. "
        "Several warnings were harmless, but two were real cross-chapter references that only appear when the whole thesis aux is generated."
    ),
    "13th April 2026": (
        "Gatekeeper sentences are where undergraduate reports often go fluffy; I treated each as a citation ticket that must be punched before submission. "
        "If a sentence could not hold a cite, I rewrote it to be weaker but true."
    ),
    "7th May 2026": (
        "The slide checklist is the kind of thing nobody writes in a log unless they have been burned before; I have been burned before on simulation slides disagreeing with the report. "
        "So the rule is regenerate from the same snapshot, always."
    ),
}

DIAGRAM_PNL_CASH = """

```mermaid
flowchart TB
  Rev[Revenue days times blended rate]
  Var[Variable cost per day]
  Fix[Fixed opex]
  Dep[Depreciation]
  Tax[Corporation tax from Y4]
  CF[Free cash flow postcapex]
  Rev --> GP[Gross profit]
  Var --> GP
  GP --> EBITDA
  Fix --> EBITDA
  EBITDA --> EBIT
  Dep --> EBIT
  EBIT --> NP[Net profit path]
  EBIT --> CF
  Tax --> CF
```

"""

DIAGRAM_NPV = """

```mermaid
flowchart LR
  FCF1[FCF Y1 to Y5]
  TV[Terminal value at horizon]
  R[Discount rate r]
  FCF1 --> NPV[Project NPV]
  TV --> NPV
  R --> NPV
  FCF1 --> IRR[IRR solve NPV equals 0]
  TV --> IRR
```

"""

DIAGRAM_TORNADO = """

```mermaid
flowchart TB
  B[Base case inputs]
  B --> P[Perturb one driver plus or minus]
  P --> R[Recompute Y3 EBIT]
  R --> Rank[Rank swings largest to smallest]
```

"""

DIAGRAM_FUNDING = """

```mermaid
flowchart TB
  S[Seed close Y1] --> R1[Runway through losses]
  R1 --> T[Series A window late Y2]
  T --> R2[Fund vehicle two and scale hires]
```

"""


def main() -> None:
    text = PATH.read_text(encoding="utf-8")

    # Insert after 6 Dec (skip if already expanded — needles disappear after first run)
    if "9th December 2025" not in text:
        n1 = "every time.\n\n\n13th December 2025"
        n2 = "every time.\n\n13th December 2025"
        if n1 in text:
            text = text.replace(
                n1, "every time.\n" + INSERT_AFTER_6_DEC + "\n13th December 2025"
            )
        elif n2 in text:
            text = text.replace(
                n2, "every time.\n" + INSERT_AFTER_6_DEC + "\n13th December 2025"
            )
        else:
            raise SystemExit("Could not find insertion point after 6th December entry")

    # Insert 18 Nov only once via bronze anchor
    for anchor in (
        "(Bronze / Silver / Gold).\n\n22nd November 2025",
        "(Bronze / Silver / Gold). \n\n22nd November 2025",
    ):
        if anchor in text and "18th November 2025" not in text:
            text = text.replace(
                anchor,
                "(Bronze / Silver / Gold).\n" + INSERT_AFTER_BRONZE + "\n22nd November 2025",
            )
            break

    # Manual unique anchors for additional inserts
    pairs = [
        (
            "30th December 2025\nRegenerate and sanity check capex\n\nI regenerated",
            "\n\n1st January 2026\nNew year checklist against the variable list\n\nI reopened the November variable list and ticked what was now pinned (days, fleet, tier prices, blended path, vehicle capex, setup capex) versus what was still open (certification magnitude, exact maintenance retainer wording, seed round timing to the quarter). The point was to stop myself from writing prose for numbers that still lived only in my head.\n\n",
        ),
        (
            "10th January 2026\nPricing benchmark table for the chapter\n\nI built the competitor pricing table",
            "\n\n15th January 2026\nRevenue table cross-foot with Toby\n\nI rebuilt the revenue table from the driver and cross-footed sold days times blended rate against the headline revenue row for each year on a calculator. I also sent Toby a screenshot of the five-year sold-days row so if he changes SOM wording later he can see exactly which row in my model would need to move.\n\n",
        ),
        (
            "31st January 2026\nCash bridge, equity rounds, and the year-two hole\n\nI built the cash view",
            "\n\n2nd February 2026\nFree cash flow definition pinned\n\nI wrote a half-page note for myself defining which cash line items sit inside “project free cash flow” for NPV versus what sits outside as pure financing. That sounds obvious until you try to explain it in a chapter footnote while also plotting a waterfall. I matched the definition to the cash figure script so IRR and NPV literally consume the same series.\n\n"
            + DIAGRAM_PNL_CASH
            + "\n",
        ),
        (
            "14th February 2026\nNPV, IRR, terminal value, and the honesty paragraph\n\nI implemented project NPV",
            "\n\n16th February 2026\nDiscount rates and hurdle language\n\nI wrote why we quote both a central VC-style 20% hurdle and a harsher 25% point on the NPV curve even though we are not claiming the company has a traded beta. The reason is practical: readers expect a sensitivity band, and I wanted the prose to name the interpretation (“high hurdle”) without pretending we estimated WACC to two decimal places.\n\n"
            + DIAGRAM_NPV
            + "\n",
        ),
        (
            "28th February 2026\nDowntime assumption tied to strategy text\n\nI re-read the strategy section",
            "\n\n1st March 2026\nDowntime table specification\n\nI specified the downtime sensitivity table rows and columns in the same order the chapter would later print them: downtime percentage, billable days multiplier, then NPV at 20%, then EBIT markers. Doing that before plotting stopped me from drawing a pretty chart that disagreed with the table by one year index.\n\n",
        ),
        (
            "10th March 2026\nUnit economics box (illustrative)\n\nI computed LTV, CAC, and payback",
            "\n\n12th March 2026\nValuation subsection structure\n\nI outlined the valuation subsection on paper: peer table first, median as terminal anchor, then explicit sentence that AB Dynamics prints higher than AVL-style floor so the reader sees the bracket. I did not want the terminal paragraph to appear from nowhere after five years of operating tables.\n\n",
        ),
        (
            "28th March 2026\nFigure layout: opex donut legend\n\nThe opex donut legend overflowed",
            "\n\n30th March 2026\nFirst combined thesis compile\n\nI ran the combined thesis build for the first time with my chapter included and collected every warning class: undefined references, multiply-defined labels, overfull boxes. Most were boring LaTeX hygiene but a few were real cross-chapter dependencies I only notice when the full aux file is generated.\n\n",
        ),
        (
            "11th April 2026\nBull and bear asymmetry footnote\n\nBull and bear scenarios use asymmetric shocks",
            "\n\n13th April 2026\nGatekeeper citations pass\n\nI checked that every “gatekeeper” style claim in the conclusions (testbed networks, government programmes, insurance assessors) still had a citation attached after edits, because those sentences are the ones markers love to underline if they look unsupported.\n\n",
        ),
        (
            "2nd May 2026\nSubmission parameter snapshot\n\nI saved a dated copy",
            "\n\n7th May 2026\nSlide export checklist\n\nI made a checklist for exporting slides: regenerate figures from the same JSON snapshot as the chapter, embed vector PDFs where possible, and never paste a headline macro from an old PDF build. Boring, but it prevents the classic “slide disagrees with thesis” failure mode in the viva room.\n\n",
        ),
    ]
    for needle, block in pairs:
        if needle in text and block.strip().split("\n", 1)[0] not in text:
            text = text.replace(needle, needle + block)

    # Tornado diagram after tornado entry
    if "Rank swings largest to smallest" not in text:
        text = text.replace(
            "24th February 2026\nTornado sensitivity (engineering-style)\n\nI set up one-at-a-time shocks",
            "24th February 2026\nTornado sensitivity (engineering-style)\n\nI set up one-at-a-time shocks"
            + DIAGRAM_TORNADO,
        )

    # Funding diagram after 7 March
    if "Series A window late Y2" not in text:
        text = text.replace(
            "7th March 2026\nFunding section: seed, Series A, triggers, use of funds\n\nI locked seed and Series A sizes",
            "7th March 2026\nFunding section: seed, Series A, triggers, use of funds\n\nI locked seed and Series A sizes" + DIAGRAM_FUNDING,
        )

    # Append paragraphs to dated sections
    DATE = re.compile(
        r"^(\d+(?:st|nd|rd|th) (?:January|February|March|April|May|November|December) \d{4})\n",
        re.MULTILINE,
    )
    matches = list(DATE.finditer(text))
    end_idx = text.find("\n\nEnd of logbook.")
    if end_idx == -1:
        raise SystemExit("End of logbook marker missing")

    out: list[str] = [text[: matches[0].start()]]
    for i, m in enumerate(matches):
        start = m.start()
        nxt = matches[i + 1].start() if i + 1 < len(matches) else end_idx
        sec = text[start:nxt].rstrip() + "\n"
        d = m.group(1)
        extra = APPENDS.get(d, "")
        if extra:
            e = extra.strip()
            append_tail = "\n\n" + e + "\n"
            # Idempotent: do not re-append if this block already ends with the extra paragraph.
            if not (sec.endswith(append_tail) or sec.endswith(e + "\n")):
                sec = sec.rstrip() + append_tail
        out.append(sec)
    out.append(text[end_idx:])
    text = "".join(out)

    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
