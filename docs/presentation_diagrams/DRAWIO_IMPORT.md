# Draw.io Automatic Import Guide

Draw.io can **automatically convert** your Mermaid diagrams into editable shapes!

## Quick Steps (Takes 2 minutes)

### Step 1: Open Draw.io
1. Go to **https://app.diagrams.net/** (or https://draw.io)
2. Click **"Create New Diagram"** (or "File" → "New" if already open)

### Step 2: Import Your Mermaid File
1. Click **"File"** → **"Import from"** → **"Device"**
2. Navigate to: `docs/presentation_diagrams/`
3. Select your `.mmd` file (e.g., `1_Main_System_Flow.mmd`)
4. Click **"Open"**

### Step 3: Draw.io Converts It!
- Draw.io will **automatically parse** your Mermaid code
- It converts it into **editable shapes** (rectangles, diamonds, ovals, etc.)
- All connections are preserved
- All text is preserved
- **Everything is now movable and editable!**

### Step 4: Edit Freely
- **Click and drag** any shape to move it
- **Double-click** any shape to edit text
- **Select shapes** to change colors, fonts, sizes
- **Drag connection points** to reroute arrows
- **Add new shapes** from the left toolbar
- **Delete shapes** with Delete key

### Step 5: Style Your Diagram
1. **Select shapes** (click or drag to select multiple)
2. Use the **format panel** on the right:
   - Change fill colors (match your original colors)
   - Change border styles
   - Adjust text formatting
   - Change fonts

### Step 6: Save
- **File** → **Save** → Choose location (Google Drive, OneDrive, or download)
- Or **File** → **Export as** → PNG/SVG/PDF

---

## What Gets Converted

| Mermaid Element | Draw.io Shape | Editable? |
|----------------|---------------|-----------|
| `([...])` Rounded rectangles | Oval/Stadium | ✅ Yes |
| `["..."]` Rectangles | Rectangle | ✅ Yes |
| `{"..."}` Diamonds | Diamond | ✅ Yes |
| Arrows `-->` | Connectors | ✅ Yes |
| Labels on arrows | Text labels | ✅ Yes |
| Styles (colors) | Fill colors | ✅ Yes (can edit) |

---

## Pro Tips

1. **Auto-layout**: After import, you can use **Arrange** → **Layout** → **Hierarchical** to auto-organize
2. **Theme**: **View** → **Theme** to change color scheme
3. **Grid/Snap**: Toggle grid and snap-to-grid for alignment
4. **Layers**: Use layers for complex diagrams
5. **Export**: Export as SVG for vector graphics (scalable) or PNG for images

---

## If Import Doesn't Work

If Draw.io doesn't recognize the `.mmd` file:

### Alternative Method 1: Use Mermaid Live First
1. Go to **https://mermaid.live/**
2. Paste your `.mmd` code
3. Click **"Actions"** → **"Download SVG"**
4. In Draw.io: **File** → **Import from** → **Device** → Select the SVG
5. SVG imports as editable shapes!

### Alternative Method 2: Copy Mermaid Code
1. In Draw.io: **Arrange** → **Insert** → **Advanced** → **Mermaid**
2. Paste your `.mmd` code
3. Click **"Insert"**
4. Draw.io converts it to editable shapes

---

## Your Files Ready to Import

All located in: `docs/presentation_diagrams/`

1. `1_Main_System_Flow.mmd` - Main flowchart
2. `2_Solver_Loop_Detail.mmd` - Solver details  
3. `3_Timestep_Calculation.mmd` - Timestep details
4. `4_System_Overview.mmd` - System overview

Import each one the same way!

---

## Comparison: Draw.io vs Miro

| Feature | Draw.io | Miro |
|---------|---------|------|
| **Auto-convert Mermaid** | ✅ Yes (direct import) | ❌ No (manual or image) |
| **Editable after import** | ✅ Yes (full editing) | ⚠️ Limited (if image) |
| **Free** | ✅ Yes | ⚠️ Limited (3 boards) |
| **Offline** | ✅ Yes (desktop app) | ❌ No |
| **Export formats** | ✅ Many (PNG, SVG, PDF, etc.) | ✅ Many |

**Draw.io is perfect for your needs!** 🎯


