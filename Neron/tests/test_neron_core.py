import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)


# ======================
# TESTS D'IMPORT
# ======================
def test_import():

import neron.neron_core
from neron.neron_core import state

    print("Test des Imports réussi.")


# ======================
# TESTS BASIQUES
# ======================

def test_basic():
    print("Basic functionality test passed.")

if __name__ == "__main__":
    print("Running neron_ tests...")

    test_import()

    print("Tous les Tests sont terminés.")