# Acceleration Phase Analysis (from simulation data)

**Config:** base_vehicle
**Total 75m time:** 3.5820 s

## Phase Boundaries (data-derived)

| Phase | Start (s) | End (s) | Duration (s) | Limiting factor |
|-------|-----------|---------|---------------|-----------------|
| 1. Initial traction | 0.000 | 0.050 | 0.050 | Torque ramp (control) |
| 2. Traction limited | 0.050 | 1.880 | 1.830 | Tire grip |
| 3. Power limited | 1.880 | 3.582 | 1.702 | 80 kW FS limit |

## Phase Details

### 1. Initial traction (torque ramp)
- **Duration:** 0.050 s (0 to 0.050 s)
- **At end:** a = 13.40 m/s², v = 0.9 km/h, P = 0.9 kW

### 2. Traction limited
- **Duration:** 1.830 s (0.050 to 1.880 s)
- **At start:** a = 13.40 m/s², P = 0.9 kW
- **At end (power limit reached):** a = 11.54 m/s², v = 84.0 km/h, P = 79.0 kW

### 3. Power limited
- **Duration:** 1.702 s (1.880 to 3.582 s)
- **At start:** a = 11.54 m/s², v = 84.0 km/h
- **At finish (75m):** a = 5.54 m/s², v = 133.9 km/h, P = 80.0 kW
