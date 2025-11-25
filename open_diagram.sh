#!/bin/bash

# Script to open the mega diagram in your default browser

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HTML_FILE="${SCRIPT_DIR}/docs/MEGA_DIAGRAM_HTML.html"

if [ -f "$HTML_FILE" ]; then
    echo "Opening mega diagram in your default browser..."
    
    # Detect OS and open accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$HTML_FILE"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open "$HTML_FILE"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        start "$HTML_FILE"
    else
        echo "Unknown OS. Please open manually: $HTML_FILE"
        exit 1
    fi
    
    echo "✓ Diagram opened!"
else
    echo "Error: HTML file not found at $HTML_FILE"
    exit 1
fi

