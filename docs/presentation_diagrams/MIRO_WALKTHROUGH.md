# Miro Walkthrough - Step by Step

## Method 1: Import as Image (Easiest - Recommended)

### Step 1: Export Your Diagram as Image
1. Go to **https://mermaid.live/**
2. Copy the entire contents of your `.mmd` file (e.g., `1_Main_System_Flow.mmd`)
3. Paste into the Mermaid Live editor
4. Click **"Actions"** button (top right)
5. Choose **"Download PNG"** (or SVG for better quality)
6. Save the file to your computer

### Step 2: Import into Miro
1. In Miro, open your board (or create new: click **"Blank board"**)
2. Click the **"+"** button in the left toolbar (or press `/` key)
3. Select **"Upload"** or **"Image"**
4. Choose the PNG/SVG file you just downloaded
5. Click to place it on the board
6. The diagram is now on your board!

### Step 3: Edit in Miro (Optional)
- **Double-click** any shape to add text
- Use **shapes** from left toolbar to recreate with Miro shapes
- Use **connectors** (arrow tool) to draw connections
- Change colors using the **format panel** (right side)

---

## Method 2: Use Miro's Flowchart Template (Best for Recreating)

### Step 1: Start with Flowchart Template
1. In Miro dashboard, click **"Flowchart"** template
2. This gives you a blank board with flowchart shapes ready

### Step 2: Add Shapes
1. Click **"+"** in left toolbar
2. Select **"Shapes"** or **"Flowchart"**
3. Choose shapes:
   - **Oval** for START/END
   - **Rectangle** for processes
   - **Diamond** for decisions
   - **Hexagon** for loops (like your SOLVE step)
   - **Predefined Process** (rectangle with lines) for function calls

### Step 3: Add Text
1. **Double-click** any shape to add text
2. Copy text from your Mermaid diagram

### Step 4: Connect Shapes
1. Click a shape to select it
2. Hover over the edge until you see **connection points** (blue dots)
3. Click and drag to another shape
4. Arrows will automatically appear

### Step 5: Style Your Diagram
1. Select shapes to change colors:
   - **START/END** (green) → Use green fill
   - **ERROR** (pink) → Use red/pink fill
   - **SOLVE** (blue) → Use blue fill
   - **INIT_MODELS** (beige) → Use beige/tan fill
2. Use the **format panel** on the right to:
   - Change fill colors
   - Change border colors
   - Adjust text size
   - Change font

---

## Method 3: Copy-Paste from Mermaid Live (If Miro Supports)

1. Go to **https://mermaid.live/**
2. Paste your `.mmd` code
3. Right-click the rendered diagram
4. **Copy image** (if available)
5. In Miro: **Ctrl+V** (or Cmd+V on Mac) to paste
6. The diagram appears as an image

---

## Quick Reference: Your Diagram Elements

Based on `1_Main_System_Flow.mmd`:

| Element | Mermaid Shape | Miro Shape | Color |
|---------|---------------|------------|-------|
| START | Rounded rectangle | **Oval** | Green (#90EE90) |
| END | Rounded rectangle | **Oval** | Green (#90EE90) |
| ERROR | Rounded rectangle | **Oval** or **Circle with X** | Pink/Red (#FFB6C6) |
| SOLVE | Rectangle | **Hexagon** (for loop) | Blue (#87CEEB) |
| INIT_MODELS | Rectangle | **Rectangle** | Beige (#FFE4B5) |
| Function calls | Rectangle | **Predefined Process** | Default |
| Decisions | Diamond | **Diamond** | Default |
| Regular processes | Rectangle | **Rectangle** | Default |

---

## Pro Tips

1. **Use Frames**: Create frames around related sections (e.g., "Initialization", "Simulation Loop", "Post-Processing")
2. **Use Sticky Notes**: Add notes explaining complex steps
3. **Use Layers**: Organize different views (overview vs. detailed)
4. **Export**: File → Export → PNG/PDF when done
5. **Collaborate**: Click "Invite members" to share with team

---

## Your Diagram Files

Located in: `docs/presentation_diagrams/`

1. `1_Main_System_Flow.mmd` - Main flowchart
2. `2_Solver_Loop_Detail.mmd` - Solver details
3. `3_Timestep_Calculation.mmd` - Timestep details
4. `4_System_Overview.mmd` - System overview

Import each one using Method 1 (easiest) or recreate using Method 2 (most editable).


