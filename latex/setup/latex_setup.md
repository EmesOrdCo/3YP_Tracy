# A Concise Guide to Setting Up LaTeX with VS Code

## Core Concept
To run LaTeX locally, you need two distinct components:
1. **A Distribution:** The engine that compiles your code into a PDF (TeX Live or MacTeX).
2. **An Editor:** The software where you write the code (VS Code).

---

## Step 1: Install the Distribution
*Note: This step installs the "brains" of LaTeX. It is a large download (4GB+) and may take some time.*

### For Windows (TeX Live)
1. Download `install-tl-windows.exe` from the [TeX Live availability page](https://www.tug.org/texlive/acquire-netinstall.html).
2. Run the installer.
3. **Crucial:** Select "Install" and ensure you wait until it completes entirely.
   * *Note:* TeX Live on Windows comes with a built-in Perl environment, which is required for VS Code automation tools.

### For macOS (MacTeX)
1. Download the **MacTeX.pkg** from the [MacTeX Website](https://www.tug.org/mactex/).
2. Run the installer and follow the standard macOS installation prompts.

> **Important:** Once the installation finishes, **restart your computer**. This ensures your system recognizes the new commands (updates the PATH).

---

## Step 2: Set up VS Code
Now that your computer "speaks" LaTeX, set up the editor.

1. Download and install **[VS Code](https://code.visualstudio.com/)**.
2. Open VS Code and click the **Extensions** view (the box icon on the left sidebar).
3. Search for and install **LaTeX Workshop** by *James Yu*.
4. (Optional) Reload VS Code to ensure the extension activates correctly.

---

## Step 3: Verify Installation
Create a simple file to test that everything is connected.

1. Run the .tex file `hello_world.tex`.
2. Next to the run button, click on the open PDF button, to view compiled document in parallel

NB: Clicking on a certain part in the PDF, jumps to that part in the code!