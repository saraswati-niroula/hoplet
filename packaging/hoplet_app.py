"""Entry point for the standalone apps built with PyInstaller (see hoplet.spec)."""
import sys

from hoplet.main import main

if __name__ == "__main__":
    sys.exit(main())
