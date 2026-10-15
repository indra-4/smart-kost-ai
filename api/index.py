import os
import sys

# Tambahkan root directory ke sys.path agar main, astar_engine, fuzzy_engine dapat diakses
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app
