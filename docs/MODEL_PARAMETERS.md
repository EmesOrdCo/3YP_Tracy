# Model Parameters

## 1. Mass Properties

| Parameter | Value | Verified | Source | Behaviour |
|-----------|-------|----------|--------|-----------|
| total_mass | 200.0 kg | ✓ Normal forces calculated | Estimated for FS vehicle | Constant |
| cg_x | 1.2 m | ✓ Weight transfer working | Assumed (75% wheelbase) | Constant |
| cg_z | 0.3 m | ✓ | Assumed typical FS | Constant |
| wheelbase | 1.6 m | ✓ | Assumed typical FS | Constant |

## 2. Tire (Pacejka)

| Parameter | Value | Verified | Source | Behaviour |
|-----------|-------|----------|--------|-----------|
| radius_loaded | 0.2286 m | ✓ | Typical 13" FSAE wheel + tire | Constant |
| rolling_resistance | 0.015 | ✓ -29N at finish | Literature (FSAE slicks) | Constant |
| pacejka_C | 1.65 | ✓ | Estimated from Avon FSAE lateral data | Constant |
| pacejka_pDx1 | 1.45 | ✓ Fx=2752N @ Fz=2000N | Estimated from Avon FSAE μ range (1.3-1.7) | Constant |
| pacejka_pDx2 | -0.08 | ✓ Load sensitivity | Tuned for μ: 1.50→1.37 over 500-3000N | Constant |
| pacejka_B | 10.0 | ✓ κ_opt=12% | Tuned for optimal slip ~12% (literature: 8-15%) | Constant |
| pacejka_E | -0.5 | ✓ | Literature typical value (negative for post-peak drop) | Constant |
| pacejka_Fz0 | 1500.0 N | ✓ | Assumed nominal rear load | Constant |

**Note:** Only pDx1 (peak μ) and C (shape factor) are derived from Avon FSAE tire data.
Other parameters (B, E, pDx2) are tuned to produce realistic behavior matching literature.

## 3. Aerodynamics

| Parameter | Value | Verified | Source | Behaviour |
|-----------|-------|----------|--------|-----------|
| cda | 0.8 m² | ✓ -706N drag at finish | Estimated typical FS (no aero) | Constant |
| cl_front | 0.0 | ✓ No downforce | Assumed (no wings modeled) | Constant |
| cl_rear | 0.0 | ✓ No downforce | Assumed (no wings modeled) | Constant |
| air_density | 1.225 kg/m³ | ✓ | Standard sea level | Constant |

## 4. Powertrain

| Parameter | Value | Verified | Source | Behaviour |
|-----------|-------|----------|--------|-----------|
| gear_ratio | 5.0 | ✓ | Optimized by simulation | Constant |
| drivetrain_efficiency | 0.95 | ✓ | Assumed (chain drive) | Constant |
| max_power | 80 kW | ✓ 80.0 kW at finish | FS Rules EV 2.2 | Constant |
| wheel_inertia | 0.1 kg·m² | ✓ | Estimated | Constant |
| battery_voltage | 600.0 V | ✓ 598.7V at finish | FS Rules max (EV 5.3.2) | Constant |
| battery_resistance | 0.01 Ω | ✓ 1.3V sag | Assumed (low for FS pack) | Constant |

## 5. Motor (YASA P400R)

| Parameter | Value | Verified | Source | Behaviour |
|-----------|-------|----------|--------|-----------|
| peak_torque | 370.0 Nm | ✓ | Datasheet: YASA P400R | Constant |
| peak_current | 450.0 A | ✓ | Datasheet: YASA P400R | Constant |
| max_speed | 838.0 rad/s (8000 RPM) | ✓ 7931 RPM at finish | Datasheet: YASA P400R | Constant |
| rated_voltage | 700.0 V | ✓ Field weakening | Datasheet: YASA P400R | Constant |
| torque_constant | 0.822 Nm/A | ✓ | Derived: 370/450 | Constant |
| base_speed @ 700V | 430.0 rad/s | ✓ | Estimated from datasheet curves | Constant |
| efficiency_peak | 0.97 | ✓ | Datasheet: YASA P400R | Constant |
| efficiency_low_load | 0.90 | ✓ | Estimated | Constant |

## 6. Supercapacitor (C46W-3R0-0600)

| Parameter | Value | Verified | Source | Behaviour |
|-----------|-------|----------|--------|-----------|
| cell_voltage | 3.0 V | ✓ | Datasheet: C46W-3R0-0600 | Constant |
| cell_capacitance | 600.0 F | ✓ | Datasheet: C46W-3R0-0600 | Constant |
| cell_ESR | 0.7 mΩ | ✓ | Datasheet: C46W-3R0-0600 | Constant |
| num_cells | 200 | ✓ | Design choice (series) | Constant |
| pack_voltage | 600.0 V initial | ✓ 455V at finish | Calculated: 3V × 200 | Variable |
| pack_capacitance | 3.0 F | ✓ | Calculated: 600F / 200 | Constant |
| pack_ESR | 0.14 Ω | ✓ | Calculated: 0.7mΩ × 200 | Constant |
| min_voltage | 350.0 V | ✓ | Inverter limit (BAMOCAR) | Constant |

## 7. Simulation

| Parameter | Value | Verified | Source | Behaviour |
|-----------|-------|----------|--------|-----------|
| dt | 1.0 ms | ✓ | Chosen for accuracy | Constant |
| max_time | 30.0 s | ✓ | Chosen (sufficient) | Constant |
| target_distance | 75.0 m | ✓ | FS Acceleration event | Constant |
| integration_method | RK4 | ✓ | Design choice | Constant |

## 8. Control

| Parameter | Value | Verified | Source | Behaviour |
|-----------|-------|----------|--------|-----------|
| launch_torque_limit | 1000.0 Nm | ✓ | Assumed (grip limited anyway) | Constant |
| target_slip_ratio | 0.15 | ✓ | Near optimal for Pacejka | Constant |
| traction_control | True | ✓ | Design choice | Constant |
