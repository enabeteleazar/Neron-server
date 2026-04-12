import subprocess

def install_packages(packages):
    for pkg in packages:
        subprocess.run(["pip", "install", pkg])

def check_package(pkg):
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False

if __name__ == "__main__":
    packages = ["ollama", "ragflow", "requests", "python-dotenv", "tqdm", "websockets", "uvicorn"]
    install_packages([p for p in packages if not check_package(p)])
    print("Dependencies checked and installed.")
