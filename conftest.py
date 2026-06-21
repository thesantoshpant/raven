import os
import sys

# Make the `raven` package importable when running pytest / scripts from the repo root.
sys.path.insert(0, os.path.dirname(__file__))
