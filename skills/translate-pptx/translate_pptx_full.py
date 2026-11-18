#!/usr/bin/env python3
"""Entry point for translate_pptx_full package.
Run: python translate_pptx_full.py <args>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from translate_pptx_full.main import main

if __name__ == "__main__":
    main(sys.argv[1:])
