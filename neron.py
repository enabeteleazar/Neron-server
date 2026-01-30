#!/usr/bin/env python3
import os
import sys
import math
import time
import random

# ===============================
# Configuration
# ===============================
FPS = 30
RADIUS = 10
CHARSET = " .:-=+*#%@"
COLOR = "\033[96m"   # Cyan Jarvis
RESET = "\033[0m"

# Clear terminal
def clear():
    sys.stdout.write("\033[2J\033[H")

def get_char(intensity):
    idx = int(intensity * (len(CHARSET) - 1))
    return CHARSET[idx]

def render_sphere(t):
    output = []
    pulse = (math.sin(t * 2) + 1) / 2  # 0 → 1

    for y in range(-RADIUS, RADIUS + 1):
        line = ""
        for x in range(-RADIUS * 2, RADIUS * 2 + 1):
            nx = x / (RADIUS * 2)
            ny = y / RADIUS
            dist = nx * nx + ny * ny

            if dist <= 1:
                z = math.sqrt(1 - dist)
                light = (
                    z * 0.7 +
                    math.sin(t + x * 0.3) * 0.15 +
                    math.cos(t * 1.5 + y * 0.3) * 0.15
                )
                light *= (0.5 + pulse * 0.5)

                light = max(0, min(1, light))
                line += get_char(light)
            else:
                line += " "
        output.append(line)

    return output

def jarvis_loop():
    t = 0.0
    try:
        while True:
            clear()
            sphere = render_sphere(t)

            print(COLOR)
            for line in sphere:
                print("   " + line)
            print(RESET)

            print("      J.A.R.V.I.S  ::  Analyse en cours...")
            print(f"      Flux neuronal : {random.randint(78,99)}%")
            print(f"      Activité IA   : STABLE")

            t += 0.05
            time.sleep(1 / FPS)

    except KeyboardInterrupt:
        clear()
        print("JARVIS hors ligne.")

if __name__ == "__main__":
    jarvis_loop()
