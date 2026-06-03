import importlib.util
import subprocess
import sys


def is_installed(package: str) -> bool:
    return importlib.util.find_spec(package) is not None


def install_packages(packages: list[str]) -> None:
    for pkg in packages:
        if is_installed(pkg):
            continue
        print(f"Module {pkg} manquant, installation...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
