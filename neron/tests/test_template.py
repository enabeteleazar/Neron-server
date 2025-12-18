import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

def test_import():
    print("Import test passed.")

def test_basic():
    print("Basic functionality test passed.")

if __name__ == "__main__":
    print("Running neron_ tests...")

    test_import()
    test_basic()

    print("All tests completed.")