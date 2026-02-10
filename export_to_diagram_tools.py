#!/usr/bin/env python3
"""
Export Mermaid diagrams to various flowchart tools.
Supports: Miro, Draw.io, Lucidchart, and image formats.
"""

import json
from pathlib import Path
from typing import List, Dict

def read_mermaid_file(file_path: Path) -> str:
    """Read Mermaid diagram code from file."""
    return file_path.read_text().strip()

def create_drawio_xml(mermaid_code: str, title: str = "Flowchart") -> str:
    """
    Create a basic Draw.io XML structure.
    Note: Draw.io can import Mermaid directly, but this provides a template.
    """
    # Draw.io prefers direct Mermaid import, but we can create a wrapper
    return f"""<mxfile>
  <diagram name="{title}" id="flowchart">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- Mermaid diagram will be imported here -->
        <!-- Use: File > Import from > Device > Select .mmd file -->
        <!-- Or: Arrange > Insert > Advanced > Mermaid -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""

def create_export_guide(diagram_files: List[Path], output_dir: Path):
    """Create a guide for exporting to different tools."""
    
    guide = f"""# Diagram Export Guide

This guide shows how to export your Mermaid diagrams to various flowchart tools.

## Your Diagrams
"""
    
    for i, diagram_file in enumerate(diagram_files, 1):
        guide += f"\n{i}. `{diagram_file.name}`\n"
    
    guide += """
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
"""
    
    output_file = output_dir / "EXPORT_GUIDE.md"
    output_file.write_text(guide)
    print(f"✓ Created export guide: {output_file}")

def create_miro_import_instructions(diagram_files: List[Path], output_dir: Path):
    """Create step-by-step instructions for Miro import."""
    
    instructions = """# Miro Import Instructions

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

"""
    
    for diagram_file in diagram_files:
        instructions += f"- `{diagram_file.name}`\n"
        # Read and show preview
        content = read_mermaid_file(diagram_file)
        lines = content.split('\n')[:3]  # First 3 lines
        instructions += f"  ```\n  {chr(10).join(lines)}...\n  ```\n\n"
    
    output_file = output_dir / "MIRO_IMPORT.md"
    output_file.write_text(instructions)
    print(f"✓ Created Miro instructions: {output_file}")

def main():
    """Main export function."""
    script_dir = Path(__file__).parent
    diagrams_dir = script_dir / "docs" / "presentation_diagrams"
    output_dir = script_dir / "docs" / "presentation_diagrams"
    
    if not diagrams_dir.exists():
        print(f"Error: {diagrams_dir} not found!")
        return
    
    # Find all .mmd files
    diagram_files = sorted(diagrams_dir.glob("*.mmd"))
    
    if not diagram_files:
        print(f"No .mmd files found in {diagrams_dir}")
        return
    
    print(f"Found {len(diagram_files)} diagram file(s):\n")
    for f in diagram_files:
        print(f"  - {f.name}")
    
    print("\n" + "="*60)
    print("Creating export guides...")
    print("="*60 + "\n")
    
    # Create guides
    create_export_guide(diagram_files, output_dir)
    create_miro_import_instructions(diagram_files, output_dir)
    
    print("\n" + "="*60)
    print("✅ Export guides created!")
    print("="*60)
    print("\n📋 Next steps:")
    print("   1. Read: docs/presentation_diagrams/EXPORT_GUIDE.md")
    print("   2. For Miro: docs/presentation_diagrams/MIRO_IMPORT.md")
    print("\n💡 Recommended: Use Draw.io (diagrams.net) for best GUI experience")
    print("   → https://app.diagrams.net/")
    print("   → File → Import from → Device → Select .mmd file")

if __name__ == "__main__":
    main()


