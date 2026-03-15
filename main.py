"""
Priorityly – entry point.
Run with:  python main.py
"""
import sys
import os

# Make sure the package is importable when running from the project root
sys.path.insert(0, os.path.dirname(__file__))

from src.app import run

if __name__ == "__main__":
    run()
