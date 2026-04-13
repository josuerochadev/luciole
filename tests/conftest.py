"""Configure le sys.path pour que les tests trouvent les modules racine."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
