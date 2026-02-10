# Miro Import Instructions

## Quick Method (Recommended)

1. **Open Miro**: https://miro.com
2. **Create new board** or open existing
3. **Click "+" button** (bottom toolbar)
4. **Select "More tools"**
5. **Search for "Mermaid"**
6. **Paste your diagram code** from the .mmd file
7. **Click "Insert"**
8. **Edit** using Miro's tools (shapes, colors, connectors)

## Alternative: Import as Image

1. **Go to Mermaid Live**: https://mermaid.live/
2. **Paste your .mmd code**
3. **Click "Actions"** → **"Download PNG"** (or SVG)
4. **In Miro**: Click **"+"** → **"Upload"**
5. **Select the downloaded image**
6. **Edit** in Miro (note: image won't be editable as flowchart)

## Your Diagram Files to Import:

- `1_Main_System_Flow.mmd`
  ```
  flowchart TD
    START([Start: JSON/YAML Config File]) --> LOAD_CONFIG["load_config<br/>config_path: str or Path"]
    ...
  ```

- `2_Solver_Loop_Detail.mmd`
  ```
  flowchart TD
    SOLVE_START([DynamicsSolver.solve Starts]) --> INIT_STATE["Initialize SimulationState<br/>position=0, velocity=0, all zeros<br/>time=0"]
    ...
  ```

- `3_Timestep_Calculation.mmd`
  ```
  flowchart TD
    DERIV_START(["_calculate_derivatives<br/>Input: state"]) --> AERO["AerodynamicsModel.calculate_forces<br/>velocity: state.velocity"]
    ...
  ```

- `4_System_Overview.mmd`
  ```
  flowchart TB
    subgraph CONFIG["CONFIG LAYER"]
        JSON["JSON/YAML File"] --> LOAD["load_config<br/>Returns: VehicleConfig"]...
  ```

