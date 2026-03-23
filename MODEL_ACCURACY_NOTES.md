# Model Accuracy Improvements

## Summary of Changes (Session: 2026-03-08)

### 1. Proper Wheel Dynamics with Slip

**Problem:** The original model forced wheel velocity to match vehicle velocity (zero slip), which meant the Pacejka tire model was never truly engaged.

**Fix:** Implemented proper wheel dynamics where:
- Wheel angular acceleration = (motor torque - tire reaction torque) / wheel_inertia
- Vehicle acceleration = tire_force / vehicle_mass
- Slip develops naturally when applied torque exceeds grip force × radius

**Files modified:**
- `dynamics/solver.py`: Rewrote `_calculate_derivatives()` to properly separate wheel and vehicle dynamics

### 2. Pacejka-Aware Traction Control

**Problem:** The `target_slip_ratio` config parameter was unused. The model had no active slip control.

**Fix:** Implemented closed-loop traction control:
- Uses wheel-to-vehicle velocity ratio as control variable
- Targets optimal slip ratio from Pacejka model (load-dependent)
- Cuts torque when wheelspin is detected (ratio > 1.18)
- Works at all speeds including launch

**Files modified:**
- `dynamics/solver.py`: Rewrote `_calculate_requested_torque()` with wheelspin-based control

### 3. Slip Ratio Logging

**Added:** New state variables for diagnostics:
- `slip_ratio_rear`: Actual rear tire slip ratio
- `optimal_slip_ratio`: Pacejka optimal slip (load-dependent)

**Files modified:**
- `dynamics/state.py`: Added new fields to SimulationState dataclass

## Current Model Behavior

### Traction Limited Phase (0-1s)
- Wheelspin briefly occurs at launch (first 10-50ms)
- Traction control rapidly reduces wheelspin
- Slip stabilizes near optimal (~0.15)
- Force utilization: ~98% of peak grip

### Power Limited Phase (1-3.6s)
- 80 kW power limit dominates
- Slip remains near optimal (tracked by TC)
- Field weakening engages at high speed

### Results with Proper Physics
| Vehicle | 75m Time | Final Velocity | Grip Utilization |
|---------|----------|----------------|------------------|
| Battery (200kg) | 3.582s | 37.19 m/s (134 km/h) | 98% (traction phase) |
| Supercapacitor (180kg) | 3.557s | 37.87 m/s (136 km/h) | 98% (traction phase) |

### Plotting: Causal Smoothing
Acceleration plots use **causal** moving average (no future-looking) to avoid boundary artifact at t=0. Centered filters were creating a fake "spike" by pulling future values into the start.

### Launch: Torque Ramp
50ms torque ramp at launch reduces jerk and slip overshoot, matching optimal FS practice.

## Pacejka Model Details

The Pacejka Magic Formula with load sensitivity is fully engaged:
- Peak μ varies with load (pDx1=1.45, pDx2=-0.12)
- Optimal slip varies with load (~0.10 at 1000N to ~0.24 at 2500N)
- Force curve has ~5% plateau around optimal (slip 0.10-0.20 gives 95%+ of peak)

## Verification

To verify the model accuracy:
```python
from config.config_loader import load_config
from dynamics.solver import DynamicsSolver
import numpy as np

config = load_config('config/vehicle_configs/base_vehicle.json')
solver = DynamicsSolver(config)
solver.solve()

# Check slip tracking
slips = np.array([s.slip_ratio_rear for s in solver.state_history])
optimal = np.array([s.optimal_slip_ratio for s in solver.state_history])
vels = np.array([s.velocity for s in solver.state_history])

moving = vels > 0.5
print(f"Mean slip: {np.mean(slips[moving]):.3f}")
print(f"Mean optimal: {np.mean(optimal[moving]):.3f}")
print(f"Tracking: {np.mean(slips[moving])/np.mean(optimal[moving])*100:.0f}%")
```

## Known Limitations

1. **Launch wheelspin:** First 10-50ms has excessive slip due to wheel inertia << vehicle mass. This is physically realistic but may need faster TC response if optimizing launch strategy.

2. **Simple TC algorithm:** Current TC uses proportional control only. Could add integral/derivative terms for tighter tracking.

3. **No tire temperature:** Model assumes constant tire grip. Real tires vary with temperature.
