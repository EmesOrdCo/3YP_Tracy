#!/usr/bin/env python3
"""
Extract the 4 diagrams from MEGA_DIAGRAM_FIXED.md for presentation use.
Creates separate .mmd files that can be rendered to images.
"""

import re
from pathlib import Path

def extract_mermaid_blocks(md_file_path):
    """Extract all mermaid code blocks from markdown file."""
    content = md_file_path.read_text()
    
    # Find all mermaid code blocks
    pattern = r'```mermaid\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    return matches

def extract_section_headers(md_file_path):
    """Extract section headers to name the diagrams."""
    content = md_file_path.read_text()
    
    # Find all markdown headers (## and ###)
    headers = re.findall(r'^(##+)\s+(.+)$', content, re.MULTILINE)
    return headers

def main():
    script_dir = Path(__file__).parent
    md_file = script_dir / "docs" / "MEGA_DIAGRAM_FIXED.md"
    output_dir = script_dir / "docs" / "presentation_diagrams"
    
    if not md_file.exists():
        print(f"Error: {md_file} not found!")
        return
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Extract mermaid blocks
    mermaid_blocks = extract_mermaid_blocks(md_file)
    
    if not mermaid_blocks:
        print("No Mermaid blocks found in the file.")
        return
    
    # Extract headers to name files
    content = md_file.read_text()
    sections = []
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('## '):
            sections.append((i, line[3:].strip()))
    
    # Map diagram indices to slide numbers and names
    diagram_names = [
        "1_Main_System_Flow",
        "2_Solver_Loop_Detail", 
        "3_Timestep_Calculation",
        "4_System_Overview"
    ]
    
    print(f"Found {len(mermaid_blocks)} Mermaid diagram(s)")
    print(f"Extracting to: {output_dir}\n")
    
    # Save each diagram
    for i, diagram_code in enumerate(mermaid_blocks[:4], 1):  # Only first 4 diagrams
        if i <= len(diagram_names):
            filename = f"{diagram_names[i-1]}.mmd"
        else:
            filename = f"diagram_{i}.mmd"
        
        output_path = output_dir / filename
        output_path.write_text(diagram_code.strip() + '\n')
        print(f"✓ Saved: {filename}")
    
    print(f"\n📋 Next steps to create images:")
    print(f"   1. Go to https://mermaid.live/")
    print(f"   2. Copy-paste the contents of each .mmd file")
    print(f"   3. Click 'Actions' → 'Download PNG' or 'Download SVG'")
    print(f"   4. Use the high-resolution images in your presentation")
    print(f"\n   OR")
    print(f"   1. Open docs/MEGA_DIAGRAM_HTML.html in your browser")
    print(f"   2. Take screenshots of each diagram section")
    print(f"   3. Crop and use in your presentation")
    print(f"\n   OR (if you have @mermaid-js/mermaid-cli installed):")
    print(f"   mmdc -i {output_dir}/*.mmd -o {output_dir}/*.png")

if __name__ == "__main__":
    main()


