from RdLib.Rd import Rd 
from RdLib.config import config
import numpy as np
import time

# Smooth settings for presence detection
config.set(Kalman=True)
config.set(distance_units="m")
config.set(Kalman_Q=np.diag([0.2, 0.2, 0.2, 0.2]))     # Higher = responsive
config.set(Kalman_R=np.diag([30, 30]))                 # Lower = trust sensor

'''
For presence detection (is someone there?):
Q_VALUE = 0.05
R_VALUE = 100
Smooth, stable — good for triggering events.

For position tracking (where exactly?):
Q_VALUE = 0.2
R_VALUE = 30
Responsive — good for following movement.

For gesture/speed detection:
Q_VALUE = 0.5
R_VALUE = 10
Very reactive — captures quick movements.
'''


rd = Rd()

ROOM_DEPTH = 3.0  # meters - adjust to your room size

while True:
    distance = rd.get_distance()
    x, y = rd.get_coordinate()
    angle = rd.get_angle()

    # present = distance < ROOM_DEPTH

    print(f"X: {x:6.2f}m  Y: {y:6.2f}m  Dist: {distance:5.2f}m  Angle: {angle:6.1f}°")
    # print(f"{'PRESENT' if present else 'EMPTY':8} | Dist: {distance:.2f}m | Angle: {angle:6.1f}°")

    time.sleep(0.3)
