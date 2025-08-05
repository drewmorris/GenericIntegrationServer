import pathlib
import sys

# Ensure project root is on sys.path so `import backend` works when tests are collected
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT)) 