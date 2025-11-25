#!/usr/bin/env python3
"""
Extract Mermaid code blocks from MEGA_DIAGRAM.md for easy copy-paste to mermaid.live
Creates separate .mmd files for each diagram section.
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
    md_file = script_dir / "docs" / "MEGA_DIAGRAM.md"
    output_dir = script_dir / "docs" / "mermaid_extracted"
    
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
    current_section = "diagram"
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('## '):
            sections.append((i, line[3:].strip()))
    
    print(f"Found {len(mermaid_blocks)} Mermaid diagram(s)")
    print(f"Extracting to: {output_dir}\n")
    
    # Save each diagram
    for i, diagram_code in enumerate(mermaid_blocks, 1):
        # Find the section name for this diagram
        section_name = f"diagram_{i}"
        
        # Look for section headers before this diagram
        diagram_pos = content.find(f"```mermaid\n{diagram_code[:50]}")
        if diagram_pos >= 0:
            # Find the last section header before this position
            for j, (pos, name) in enumerate(sections):
                if pos < diagram_pos:
                    section_name = name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
        
        filename = f"{section_name}.mmd"
        output_path = output_dir / filename
        
        output_path.write_text(diagram_code.strip() + '\n')
        print(f"✓ Saved: {filename}")
    
    # Create a combined file with all diagrams
    combined = output_dir / "ALL_DIAGRAMS.mmd"
    combined_content = "\n\n---\n\n".join([block.strip() for block in mermaid_blocks])
    combined.write_text(combined_content + '\n')
    print(f"\n✓ Combined file: ALL_DIAGRAMS.mmd")
    
    print(f"\n📋 Next steps:")
    print(f"   1. Go to https://mermaid.live/")
    print(f"   2. Copy-paste the contents of any .mmd file from {output_dir}")
    print(f"   3. Or open ALL_DIAGRAMS.mmd to see all diagrams at once")

if __name__ == "__main__":
    main()

