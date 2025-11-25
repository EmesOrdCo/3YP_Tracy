"""Setup script for Formula Student Acceleration Simulation."""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path) as f:
        long_description = f.read()

setup(
    name="formula-student-acceleration",
    version="1.0.0",
    description="Formula Student acceleration event simulation and optimization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Formula Student Team",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.7",
    entry_points={
        'console_scripts': [
            'fs-optimize=examples.quick_optimization:main',
            'fs-simulate=examples.basic_run:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

