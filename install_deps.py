import subprocess
import sys

def install_packages(packages: list[str]):
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            print(f"Module {pkg} manquant, installation...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
