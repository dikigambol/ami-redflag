import sys
import os

# Menambahkan root direktori ke sys.path agar main.py dapat diimport di Vercel Serverless
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from main import app
