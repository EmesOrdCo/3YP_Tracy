# Diagram Export Guide

This guide shows how to export your Mermaid diagrams to various flowchart tools.

## Your Diagrams

1. `1_Main_System_Flow.mmd`

2. `2_Solver_Loop_Detail.mmd`

3. `3_Timestep_Calculation.mmd`

4. `4_System_Overview.mmd`

---

## Option 1: Miro (Best for Collaboration)

### Method A: Direct Mermaid Import
1. Open Miro (https://miro.com)
2. Create a new board
3. Click **"+"** → **"More tools"** → Search **"Mermaid"**
4. Paste your `.mmd` file contents
5. Click **"Insert"**
6. Edit with Miro's GUI tools

### Method B: Import as Image
1. Go to https://mermaid.live/
2. Paste your `.mmd` code
3. Click **"Actions"** → **"Download PNG"** or **"Download SVG"**
4. In Miro: Click **"+"** → **"Upload"** → Select the image
5. Or drag-and-drop the image file

---

## Option 2: Draw.io / diagrams.net (Best Free Option)

### Direct Mermaid Import
1. Go to https://app.diagrams.net/
2. **File** → **Import from** → **Device**
3. Select your `.mmd` file
4. Click **"Open"**
5. Edit with full GUI controls

### Alternative: Insert Mermaid
1. Open Draw.io
2. **Arrange** → **Insert** → **Advanced** → **Mermaid**
3. Paste your `.mmd` code
4. Click **"Insert"**

**Features:**
- ✅ Free and open-source
- ✅ Excellent GUI for editing
- ✅ Export to PNG, SVG, PDF, etc.
- ✅ Can save to Google Drive, OneDrive, or local

---

## Option 3: Lucidchart

1. Go to https://www.lucidchart.com/
2. Create a new document
3. **File** → **Import** → **Import File**
4. Select your `.mmd` file (if supported) OR:
5. Use Mermaid Live Editor to export as SVG/PNG first, then import

---

## Option 4: Mermaid Live Editor (Quick Export)

1. Go to https://mermaid.live/
2. Paste your `.mmd` code
3. Click **"Actions"** → Choose format:
   - **Download PNG** (for presentations)
   - **Download SVG** (for editing in vector tools)
   - **Download PDF** (for documents)

Then import the image into your preferred tool.

---

## Option 5: VS Code with Mermaid Extension

1. Install **"Markdown Preview Mermaid Support"** extension
2. Open your `.mmd` file
3. Right-click → **"Export Diagram"** → Choose format
4. Import the exported file into your tool

---

## Recommended Workflow

**For Quick Editing:**
1. Use **Draw.io** (diagrams.net) - best free GUI
2. Import `.mmd` directly
3. Edit with visual tools
4. Export to PNG/SVG when done

**For Collaboration:**
1. Use **Miro** - best for team collaboration
2. Import Mermaid or image
3. Share board with team
4. Real-time collaboration

**For Documentation:**
1. Use **Mermaid Live Editor** to export as SVG
2. Embed in documentation
3. Or use Draw.io for more control

---

## Quick Commands

### Export all diagrams to images (requires mermaid-cli):
```bash
# Install mermaid-cli first:
npm install -g @mermaid-js/mermaid-cli

# Then export:
mmdc -i docs/presentation_diagrams/*.mmd -o docs/presentation_diagrams/images/
```

### View diagrams in browser:
```bash
# Open the HTML file:
open docs/MEGA_DIAGRAM_HTML.html
```

---

## File Locations

Your diagram files are in:
- `docs/presentation_diagrams/*.mmd`

Export them using any method above!
