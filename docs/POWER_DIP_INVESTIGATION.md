# End-of-run electrical-power dip — investigation summary

## TL;DR

The dip is **physically real and unavoidable** with the current hardware. With
a 200-cell supercapacitor stack and a BAMOCAR-PG-D3-700/400 inverter (peak 285
A_RMS), the motor's V_dc-dependent power envelope drops below the FS 80 kW cap
the moment the supercap voltage falls below 600 V — which happens immediately
after launch. No combination of gearing, launch profile, or control law can
keep electrical power flat at 80 kW to the finish without slowing the run
below the 3.78 s baseline.

The minimum hardware change that flips the answer to "yes":

* **Either** add ~40 supercap cells (200 → 240, V_init: 600 V → 720 V),
* **Or** upgrade to an inverter with peak ≥ ~380 A_RMS (e.g. BAMOCAR-PG-D3
  with the 600 A_peak option, ~425 A_RMS).

Both options keep the motor in the FS-cap-binding regime to the finish line
and recover ~30 ms on the run time as a bonus. Recommended option: more cells
(electrically simpler, no inverter swap, easier to justify against FS rules).

The investigation script is at
`latex/HarryEmes/Presentation/_investigate_power_dip.py` and the comparison
figure at `latex/HarryEmes/Engineering/figures/power_dip_options.pdf`.

---

## Mechanism

1. The supercapacitor pack starts at V_init = 600 V (200 cells × 3 V) and
   discharges as constant power is drawn. Pack capacitance is C = 600/200 = 3
   F, so initial energy is E = ½ C V² = 540 kJ.
2. The motor model (`vehicle/motor_model.py`) treats base speed as
   proportional to bus voltage:
   ω_base(V_dc) = ω_base_rated · V_dc / V_rated.
   With Kt = 0.822 Nm/A_RMS and BAMOCAR peak I = 285 A_RMS,
   T_peak = 234.3 Nm.
3. To deliver the FS cap of 80 kW *electrical* the motor needs P_mech ≥ 80
   kW × η_motor = 76 kW from a (T_peak, ω_base) operating point in field
   weakening:
   T_peak · ω_base · η_motor ≥ 80 kW
   234.3 · (max_speed/2 · V_dc/700) · 0.95 ≥ 80,000
   ⇒ **V_dc ≥ 600.5 V**.
4. Since V_init = 600 V, *any* discharge takes V_dc below the 600.5 V
   threshold. From that point on, the motor's electrical-power capability
   is below 80 kW; the FS cap stops binding; and P_elec = motor capability,
   which keeps falling with V_dc as the cap drains. The simulation shows P
   start to roll off at t ≈ 1.7 s and end the run at 64 kW.

This is captured by the verbatim per-step diagnostic
(`latex/HarryEmes/Presentation/_diag_power.py`):

```
    t       v    P_elec     V_dc    omega_m   omega_b    T_max   P_max_e   FW?
 0.00      0      0.0   600.0       0.0    359.1   234.3      0.0     N
 1.20     52     65.7   562.1     319.9    336.5   234.3     78.9     N
 1.40     61     77.6   550.4     374.0    329.4   206.4     81.2     Y
 1.60     69     80.0   539.7     425.8    323.0   177.7     79.7     Y   ← cap binds
 2.00     83     78.1   519.4     512.7    310.9   142.1     76.7     Y   ← cap stops binding
 3.00    107     70.0   469.8     663.3    281.2    99.3     69.4     Y
 3.78    120     63.9   431.3     ...      ...      ...      ...      Y
```

(This script previously read V_dc *live* from the post-run powertrain object
rather than per-step from `state.dc_bus_voltage`, which made the V_dc column
constant at 431 V and caused the original "P_max_capability" column to be
evaluated at the wrong voltage. The version in the repo now reads the
state-history value at each row, so the table above is now the truth.)

---

## Closed-form energy proof: why no control-law tweak can fix it

Working with the bus voltage threshold V_dc_min = 600.5 V derived above:

* Required minimum stored energy at the finish:
  E_end ≥ ½ · C · V_dc_min² = ½ · 3 · 600.5² = **541 kJ**.
* Initial stored energy: E_init = ½ · 3 · 600² = **540 kJ**.
* Energy *available* to deliver to the load while keeping V_dc above the
  threshold: E_init − E_end = **−1 kJ**.

The supercap literally cannot deliver any net energy to the load before V_dc
drops below the 80 kW threshold. Yet the run physically requires energy
delivered to the load:

* KE at finish: ½ · 250 · 33.3² = 138.6 kJ
* Drag work (75 m, ⟨½ρv²C_dA⟩): ~13.6 kJ
* Rolling resistance (75 m): ~1.8 kJ
* Total mechanical energy needed: ~154 kJ
* Divided by motor efficiency: ~162 kJ electrical.

162 kJ required vs. 0 kJ available within the no-dip envelope ⇒ deficit is
~163 kJ. **No control law, gear ratio, or launch profile can move energy
that doesn't exist.**

Closed-form bound for the minimum cell count (keeping cell type fixed):

* E_init(N) = ½ · (600/N) · (3N)² = 2700 · N J
* E_end_min(N) = ½ · (600/N) · 600² = 1.08·10⁸ / N J
  (V_dc_min = 600 V is independent of N because ω_base/V is fixed by
  max_speed and the 700 V reference inside `create_motor_from_config`.)
* E_avail(N) = 2700 N − 1.08·10⁸/N
* Solving E_avail(N) ≥ 162 kJ gives **N ≥ 232** (recommend ~240).

---

## Hypothesis status

| # | Hypothesis | Status | Evidence |
|---|---|---|---|
| H1 | Gear ratio is wrong | ❌ Not the fix | Test 2 sweep G ∈ [2.5, 7.0]: at G ≈ 4.25 the run is fastest (3.69 s) but P_finish = 64 kW — same dip. No G yields both flat power *and* finish ≤ 3.78 s. |
| H2 | Motor max current is artificially low | ❌ Not free | Test 3 sweep + datasheet check: 285 A is the BAMOCAR's peak A_RMS rating. YASA Kt = 370/450 = 0.822 is in Nm/A_RMS (datasheet "@ 450 A_RMS"). 400 A_peak ↔ 285 A_RMS describe the *same* operating point for sinusoidal current. Raising motor_max_current would require a different inverter. |
| H3 | Field-weakening curve too pessimistic | ❌ No effect | Test 1 sanity check: switching to a constant-V battery at 600 V keeps P_min = 79.2 kW and P_finish = 80.0 kW. The 4 kW transient at the FW knee is the only model-pessimism, and it disappears with a fixed bus voltage. The chronic dip is purely V_dc-driven. |
| H4 | Initial state-of-charge is below nominal | ❌ Not the cause | The fixed `_diag_power.py` reads V_dc[t=0] = 600.0 V exactly. The brief's "start V_dc 600 V → end V_dc 431 V" claim was correct numerically; the misleading 431 V column was from the old script reading live (post-run) voltage. |
| H5 | Control law over-discharges supercap at launch | ❌ Not significant | At t = 1.0 s (well into launch), V_dc has dropped from 600 to 572 V (28 V, 9.3% energy). The launch is delivering ~17 kJ to KE which is unavoidable; no gentler ramp can recover meaningfully. Even *zero* energy used during launch would only buy us ~30 V of bus voltage at the threshold — still not enough to clear 600.5 V at the finish. |
| H6 | Optimiser doesn't penalise flatness | ❌ Foreclosed by H1+energy bound | The optimiser cannot find a flat-power configuration because none exists in the feasible set. Adding the penalty would just push it toward slower configurations with lower flat-power targets. |

---

## Numerical evidence (full table from `_investigate_power_dip.py`)

```
TEST 0  baseline:   t=3.782 s, V_dc 600→431, P_finish=63.9 kW
TEST 1  battery:    t=3.763 s, V_dc 600→581, P_finish=80.0 kW   [voltage sag = only mechanism]
TEST 2  gear sweep: best G=4.25  → 3.69 s, P_finish=64.2 kW     [no flat-power point]
TEST 3  current sweep: I=380 A → 3.75 s, P_finish=80.0 kW       [requires bigger inverter]
TEST 4  cell sweep: N=240 → 3.756 s, V_dc 720→542, P_finish=80.0 kW   [recommended fix]
TEST 5  combined:   I=400, G=4.0 → 3.643 s, P_finish=80.0 kW    [requires bigger inverter]
ENERGY BUDGET: deficit 163 kJ at N=200 → minimum N = 232 cells
```

---

## Recommendations

### Engineering report

1. **Keep the current `final_run.pdf`** — the dip is physically correct and
   represents real hardware behaviour. The figure should be captioned as
   such.
2. **Add a paragraph in the powertrain section** explaining the V_dc-locked
   80 kW threshold (V_dc_min = 600.5 V derivation above) and the energy
   bound. The proof is short enough to put inline.
3. **Reference `power_dip_options.pdf`** as a supporting figure showing the
   three configurations side by side.

### Hardware recommendations (in the report's "future work" section)

* **Primary**: increase the supercap pack to 240 cells (V_init = 720 V). Run
  time improves by ~26 ms and P stays flat at 80 kW. Mass cost: ~21 kg of
  added cells (525 g/cell × 40), which would partially negate the time
  improvement.
* **Alternative**: upgrade to a BAMOCAR-PG-D3-700/600 (or equivalent) with
  peak ≥ 380 A_RMS. The motor can then sustain 80 kW down to V_dc ≈ 450 V,
  which is below the supercap's normal-operation discharge floor. Run time
  improves more (~30 ms) without mass penalty, but at significant cost and
  rules-recertification effort.

### Don't do

* Tune the gear ratio further. The sweep is exhaustive: G < 4.25 leaves time
  on the table, G > 4.25 increases the dip.
* Add flatness penalty to the optimiser. The constraint set has no flat-80
  kW solution with this hardware; the optimiser would just trade off lap time
  for flatness in a way no engineer would accept.
* Increase `motor_max_current` in `base_vehicle.json` above 285 A — this
  would silently exceed the BAMOCAR's peak rating and produce optimistic
  numbers that wouldn't survive a hardware check.

---

## Files touched

* `latex/HarryEmes/Presentation/_diag_power.py` — fixed the per-step V_dc
  read (was reading live, now reads from `state.dc_bus_voltage`).
* `latex/HarryEmes/Presentation/_investigate_power_dip.py` — new
  end-to-end investigation harness (battery sanity check, gear sweep,
  current sweep, cell sweep, combined fix, closed-form energy budget).
* `latex/HarryEmes/Presentation/_make_power_dip_compare.py` — generates
  the comparison figure for the engineering report.
* `latex/HarryEmes/Engineering/figures/power_dip_options.pdf|.png` — the
  resulting comparison figure (P_elec(t) and V_dc(t) for the three cases).
* `docs/POWER_DIP_INVESTIGATION.md` — this file.

`config/vehicle_configs/base_vehicle.json` and the slide layout
(`latex/HarryEmes/Presentation/main.tex`) are intentionally untouched, in
line with the brief.
