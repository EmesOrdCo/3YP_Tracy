#!/usr/bin/env python3
"""
Build the logbook HTML from LOGBOOK.md

Usage:
    python build_logbook.py

This converts LOGBOOK.md to figures/LOGBOOK_COMPLETE.html with nice formatting.
"""

import re
from pathlib import Path
from datetime import datetime

def convert_logbook():
    project_root = Path(__file__).parent
    md_file = project_root / "LOGBOOK.md"
    html_file = project_root / "figures" / "LOGBOOK_COMPLETE.html"
    
    # Read markdown
    content = md_file.read_text()
    
    # Extract title from first line
    all_lines = content.split('\n')
    doc_title = all_lines[0].strip() if all_lines else "Development Logbook"
    
    # HTML template
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Formula Student Acceleration Simulation — Development Logbook</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;1,400&family=Source+Sans+Pro:wght@400;600&display=swap');
        
        :root {{
            --text-color: #2c2c2c;
            --heading-color: #1a1a1a;
            --accent-color: #8B0000;
            --border-color: #ddd;
            --bg-light: #fafafa;
        }}
        
        * {{ box-sizing: border-box; }}
        
        body {{
            font-family: 'Crimson Pro', Georgia, serif;
            font-size: 17px;
            line-height: 1.7;
            color: var(--text-color);
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #fff;
        }}
        
        h1 {{
            font-family: 'Source Sans Pro', sans-serif;
            font-size: 28px;
            font-weight: 600;
            color: var(--heading-color);
            text-align: center;
            margin-bottom: 50px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--accent-color);
        }}
        
        .entry {{ margin-bottom: 45px; page-break-inside: avoid; }}
        
        .date {{
            font-family: 'Source Sans Pro', sans-serif;
            font-size: 15px;
            font-weight: 600;
            color: var(--accent-color);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }}
        
        .entry-title {{
            font-family: 'Source Sans Pro', sans-serif;
            font-size: 16px;
            font-weight: 600;
            color: var(--heading-color);
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        p {{ margin: 0 0 16px 0; text-align: justify; hyphens: auto; }}
        
        .equation {{
            font-family: 'Courier New', monospace;
            font-size: 15px;
            background: var(--bg-light);
            padding: 12px 16px;
            margin: 16px 0;
            border-left: 3px solid var(--accent-color);
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        
        ul, ol {{ margin: 16px 0; padding-left: 24px; }}
        li {{ margin-bottom: 8px; }}
        
        .figure {{ margin: 30px 0; text-align: center; }}
        .figure img {{
            max-width: 100%;
            height: auto;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .figure-caption {{
            font-family: 'Source Sans Pro', sans-serif;
            font-size: 13px;
            color: #666;
            margin-top: 10px;
            font-style: italic;
        }}
        
        .mermaid {{
            margin: 25px 0;
            padding: 20px;
            background: var(--bg-light);
            border: 1px solid var(--border-color);
            text-align: center;
        }}
        
        .code-block {{
            font-family: 'Courier New', monospace;
            font-size: 13px;
            background: #f5f5f5;
            padding: 16px;
            margin: 16px 0;
            border: 1px solid var(--border-color);
            overflow-x: auto;
            white-space: pre;
        }}
        
        .section-break {{
            text-align: center;
            margin: 50px 0;
            color: var(--accent-color);
        }}
        .section-break::before {{
            content: "• • •";
            letter-spacing: 8px;
        }}
        
        @media print {{
            body {{ font-size: 11pt; max-width: 100%; padding: 0; }}
            .entry {{ page-break-inside: avoid; }}
            .figure {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>

<h1>{title}</h1>

<div style="text-align: center; font-size: 12px; color: #999; margin-bottom: 30px;">
    Generated: {timestamp}
</div>

{entries}

<script>
    mermaid.initialize({{ 
        startOnLoad: true, 
        theme: 'neutral',
        flowchart: {{ useMaxWidth: true, htmlLabels: true }}
    }});
</script>

</body>
</html>'''

    # Parse entries from markdown
    # Format expected: 
    # ---
    # **DATE**
    # TITLE
    # 
    # Content...
    
    entries_html = []
    
    # Split by date pattern (e.g., "4th November 2025" or "1st December 2025")
    date_pattern = r'\n\n(\d{1,2}(?:st|nd|rd|th) (?:November|December|January) \d{4})\n([^\n]+)\n'
    
    parts = re.split(date_pattern, content)
    
    # parts[0] is the header, then groups of (date, title, content)
    i = 1
    while i < len(parts) - 2:
        date = parts[i]
        title = parts[i + 1]
        
        # Find the content (everything until the next date or end)
        if i + 3 < len(parts):
            content_text = parts[i + 2]
        else:
            content_text = parts[i + 2] if i + 2 < len(parts) else ""
        
        # Convert content to HTML
        entry_html = convert_entry_to_html(date, title, content_text)
        entries_html.append(entry_html)
        
        i += 3
    
    # Combine all entries
    all_entries = '\n\n'.join(entries_html)
    
    # Generate final HTML
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_html = html_template.format(entries=all_entries, timestamp=timestamp, title=doc_title)
    
    # Write output
    html_file.write_text(final_html)
    print(f"Generated: {html_file}")
    print(f"Open with: open {html_file}")


def convert_entry_to_html(date: str, title: str, content: str) -> str:
    """Convert a single entry to HTML."""
    
    # Process content
    lines = content.strip().split('\n')
    html_parts = []
    
    in_equation = False
    in_mermaid = False
    in_code = False
    in_list = False
    list_type = None
    equation_lines = []
    mermaid_lines = []
    code_lines = []
    list_items = []
    
    for line in lines:
        stripped = line.strip()
        
        # Check for mermaid blocks
        if stripped == '```mermaid':
            in_mermaid = True
            mermaid_lines = []
            continue
        elif in_mermaid and stripped == '```':
            in_mermaid = False
            html_parts.append(f'<div class="mermaid">\n' + '\n'.join(mermaid_lines) + '\n</div>')
            continue
        elif in_mermaid:
            mermaid_lines.append(line)
            continue
        
        # Check for code blocks
        if stripped.startswith('```') and not in_code:
            in_code = True
            code_lines = []
            continue
        elif in_code and stripped == '```':
            in_code = False
            html_parts.append('<div class="code-block">' + '\n'.join(code_lines) + '</div>')
            continue
        elif in_code:
            code_lines.append(line)
            continue
        
        # Check for images
        img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', stripped)
        if img_match:
            alt = img_match.group(1)
            src = img_match.group(2)
            html_parts.append(f'<div class="figure">\n<img src="{src}" alt="{alt}">\n<div class="figure-caption">{alt}</div>\n</div>')
            continue
        
        # Check for lists
        if stripped.startswith('- '):
            if not in_list:
                in_list = True
                list_type = 'ul'
                list_items = []
            list_items.append(stripped[2:])
            continue
        elif re.match(r'^\d+\. ', stripped):
            if not in_list:
                in_list = True
                list_type = 'ol'
                list_items = []
            list_items.append(re.sub(r'^\d+\. ', '', stripped))
            continue
        elif in_list and stripped == '':
            # End of list
            tag = list_type
            items_html = '\n'.join([f'<li>{item}</li>' for item in list_items])
            html_parts.append(f'<{tag}>\n{items_html}\n</{tag}>')
            in_list = False
            list_items = []
            continue
        elif in_list and not stripped.startswith('-') and not re.match(r'^\d+\. ', stripped):
            # End of list
            tag = list_type
            items_html = '\n'.join([f'<li>{item}</li>' for item in list_items])
            html_parts.append(f'<{tag}>\n{items_html}\n</{tag}>')
            in_list = False
            list_items = []
        
        # Check for equations (lines with = or × or mathematical content)
        if stripped and (
            '=' in stripped and any(c.isalpha() for c in stripped) and 
            not stripped.startswith('<') and
            ('×' in stripped or '/' in stripped or '+' in stripped or '-' in stripped or
             re.search(r'[A-Za-z].*=.*[A-Za-z0-9]', stripped))
        ):
            # This looks like an equation
            html_parts.append(f'<div class="equation">{stripped}</div>')
            continue
        
        # Check for section breaks
        if stripped == '---':
            html_parts.append('<div class="section-break"></div>')
            continue
        
        # Regular paragraph
        if stripped:
            html_parts.append(f'<p>{stripped}</p>')
    
    # Close any open list
    if in_list:
        tag = list_type
        items_html = '\n'.join([f'<li>{item}</li>' for item in list_items])
        html_parts.append(f'<{tag}>\n{items_html}\n</{tag}>')
    
    content_html = '\n\n'.join(html_parts)
    
    return f'''<div class="entry">
<div class="date">{date}</div>
<div class="entry-title">{title}</div>
{content_html}
</div>'''


if __name__ == "__main__":
    convert_logbook()
