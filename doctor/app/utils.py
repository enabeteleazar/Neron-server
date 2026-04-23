# app/utils.py
# optionnel evolutif

import subprocess

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True)
    except Exception as e:
        return str(e)
