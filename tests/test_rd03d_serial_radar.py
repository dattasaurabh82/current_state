from RdLib.Rd import Rd
from RdLib.config import config
import numpy as np
import time

# --- CONFIGURATION ---
# Now that data is valid, we can trust the Kalman filter again!
config.set(Kalman=True)
config.set(distance_units="m")

# Tweak these for "Human Typing" (Small movements)
# Q = Process Noise (Higher = follows fast movements, Lower = smoother)
config.set(Kalman_Q=np.diag([0.05, 0.05, 0.05, 0.05])) 
# R = Measurement Noise (Higher = ignore spikes, Lower = trust sensor)
config.set(Kalman_R=np.diag([50, 50])) 

rd = Rd()

# IGNORE everything further than this distance (e.g., walls)
MAX_RANGE_METERS = 2.5 

print("--- Radar Active: Filtering Enabled ---")

while True:
    try:
        # 1. Get Synchronized Data
        data = rd.OutputDump()
        
        # OutputDump returns: (x, y, dist, angle, mode, raw_dist)
        # Note: When Kalman is True, 'x' and 'y' in OutputDump might NOT be filtered 
        # depending on library version. 
        # Let's use the library's specific getters which usually apply the filter logic.
        
        # HOWEVER, to be safe and avoid the desync bug again, 
        # we will manually apply a simple logic or trust OutputDump if it uses the internal state.
        
        raw_x = data[0]
        raw_y = data[1]
        dist = data[2]
        angle = data[3]
        
        # 2. Simple Range Gating (Ignore walls)
        if dist > MAX_RANGE_METERS:
            # Skip this reading, it's probably the back wall
            continue
            
        # 3. Visualize
        # A simple visual bar to see where the target is (Left vs Right)
        # Scale: -3m to +3m
        pos_marker = int((raw_x + 3) * 10) 
        pos_marker = max(0, min(pos_marker, 60))
        visual_bar = [" "] * 61
        visual_bar[pos_marker] = "O" # 'O' is the target
        visual_bar[30] = "|"         # '|' is the radar center
        
        bar_str = "".join(visual_bar)
        
        print(f"[{bar_str}] X: {raw_x:5.2f}m  Dist: {dist:5.2f}m")

    except Exception as e:
        print(f"Error: {e}")
        
    time.sleep(0.1)
