import random
import math
import time

class Satellite: 

    # Represents a satellite node in the consensus network.
    def __init__(self, node_id, orbit_radius, orbit_speed):
        self.node_id          = node_id
        self.orbit_radius     = orbit_radius
        self.orbit_speed      = orbit_speed
        self.angle            = random.uniform(0, 2 * math.pi)

        # Status
        self.online           = True
        self.is_faulty        = False

        # Sensor readings
        self.temperature      = round(random.uniform(-25, 5), 2)
        self.signal_strength  = round(random.uniform(-85, -55), 2)
        self.altitude         = round(random.uniform(470, 530), 2)

        # Consensus state
        self.role             = "follower"   # follower | candidate | leader
        self.votes_received   = 0
        self.current_leader   = None
        self.log              = []

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    @staticmethod
    def _step_toward(current, target, max_delta):
        delta = target - current
        delta = Satellite._clamp(delta, -max_delta, max_delta)
        return current + delta
    # Satellite behavior methods

    def update_position(self):
        self.angle = (self.angle + self.orbit_speed) % (2 * math.pi) # 
        # In a real implementation, this would also update the satellite's position in space,
        # but here we just update the angle for testing. 

    def get_xy(self, cx, cy):
        x = cx + self.orbit_radius * math.cos(self.angle) 
        y = cy + self.orbit_radius * math.sin(self.angle)
        return x, y
        # In a real implementation, this would return the satellite's actual position in space,
        # but here we just calculate a position based on the orbit for testing.

    def collect_sensor_data(self):
        if not self.online:
            return None

        if self.is_faulty:
            # Faulty nodes still drift, but toward clearly bad ranges.
            target_temp = random.uniform(500, 1000)
            target_sig = random.uniform(-200, -150)
            target_alt = random.uniform(50000, 99999)

            self.temperature = self._step_toward(self.temperature, target_temp, 80.0)
            self.signal_strength = self._step_toward(self.signal_strength, target_sig, 25.0)
            self.altitude = self._step_toward(self.altitude, target_alt, 12000.0)
        else:
            target_temp = random.uniform(-80, 20)
            target_sig = random.uniform(-100, -40)
            target_alt = random.uniform(400, 600)

            # If currently out-of-family, recover faster back to nominal ranges.
            temp_step = 15.0 if not (-90 <= self.temperature <= 50) else 2.5
            sig_step = 8.0 if not (-120 <= self.signal_strength <= -30) else 1.8
            alt_step = 3000.0 if not (300 <= self.altitude <= 700) else 8.0

            self.temperature = self._step_toward(self.temperature, target_temp, temp_step)
            self.signal_strength = self._step_toward(self.signal_strength, target_sig, sig_step)
            self.altitude = self._step_toward(self.altitude, target_alt, alt_step)

        self.temperature = round(self.temperature, 2)
        self.signal_strength = round(self.signal_strength, 2)
        self.altitude = round(self.altitude, 2)
        # In a real implementation, this would read from actual sensors, but here we just generate random data for testing.
        # Faulty satellites generate out-of-range data to simulate sensor failures.
        # Online satellites generate normal data, while offline satellites return None.
        # offline satellites are handled by returning None, which the network can use to identify them.

        return {
            "node_id":         self.node_id,
            "temperature":     self.temperature,
            "signal_strength": self.signal_strength,
            "altitude":        self.altitude,
            "timestamp":       time.time()
        }
        # In a real implementation, this would send data to the consensus algorithm
        # and other nodes, but here we just return the data for testing.
    def status(self):
        if not self.online:
            state = "OFFLINE"
        elif self.is_faulty:
            state = "FAULTY"
        else:
            state = "OK"

        return (
            f"[{self.node_id}] "
            f"Role: {self.role:<10} "
            f"Status: {state:<7} "
            f"Temp: {self.temperature:>8.2f}C  "
            f"Signal: {self.signal_strength:>8.2f} dBm  "
            f"Alt: {self.altitude:>8.2f} km"
        )


def create_default_satellites():
    """Create the shared default satellite setup used by demos/tests."""
    satellites = [
        Satellite("SAT-1", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-2", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-3", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-4", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-5", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-6", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-7", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-8", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-9", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-10", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-11", orbit_radius=200, orbit_speed=0.02),
        Satellite("SAT-12", orbit_radius=200, orbit_speed=0.02),
    ]

    for idx in (2, 7):
        satellites[idx].is_faulty = True  # SAT-3 and SAT-8 send bad data
    for idx in (4, 10):
        satellites[idx].online = False  # SAT-5 and SAT-11 are offline

    return satellites



if __name__ == "__main__":
    satellites = create_default_satellites()

    print("=" * 65)
    print(" SATELLITE NETWORK — INITIAL READINGS")
    print("=" * 65)

    for sat in satellites:
        sat.collect_sensor_data()
        print(sat.status())