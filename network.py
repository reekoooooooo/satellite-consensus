import time

class Network:
    def __init__(self, satellites):
        self.satellites = satellites        # List of all Satellite objects
        self.message_log = []              # History of all messages sent
        self.outlier_threshold = {
            "temperature":     (-90, 50),   # Normal range in Celsius
            "signal_strength": (-120, -30), # Normal range in dBm
            "altitude":        (300, 700),  # Normal range in km
        }

    # Broadcasting and Messaging

    def broadcast(self, sender):
        """Sender collects its data and sends it to all online peers."""
        if not sender.online:
            return

        data = sender.collect_sensor_data()
        if data is None:
            return

        recipients = [
            s for s in self.satellites
            if s.node_id != sender.node_id and s.online
        ]

        for recipient in recipients:
            self._deliver(sender, recipient, data)

    def _deliver(self, sender, recipient, data):
        """Simulate delivering a message from sender to recipient."""
        message = {
            "from":      sender.node_id,
            "to":        recipient.node_id,
            "data":      data,
            "timestamp": time.time(),
            "flagged":   self.is_outlier(data),
        }
        self.message_log.append(message)

    #  Outlier Detection 

    def is_outlier(self, data):
        """Returns True if any reading is outside the expected range."""
        for field, (low, high) in self.outlier_threshold.items():
            value = data.get(field, 0)
            if not (low <= value <= high):
                return True
        return False

    def collect_all_readings(self):
        """Gather one reading from every online satellite."""
        readings = []
        for sat in self.satellites:
            data = sat.collect_sensor_data()
            if data:
                data["flagged"] = self.is_outlier(data)
                readings.append(data)
        return readings

    #  Network Health 

    def get_healthy_nodes(self, readings=None):
        """Return satellites that are online and not sending bad data."""
        if readings is None:
            readings = self.collect_all_readings()
        healthy_ids = {r["node_id"] for r in readings if not r["flagged"]}
        return [s for s in self.satellites if s.node_id in healthy_ids]

    def get_status_report(self):
        """Print a full network health summary."""
        readings = self.collect_all_readings()

        print("=" * 65)
        print(" NETWORK STATUS REPORT")
        print("=" * 65)

        for r in readings:
            flag = " <-- FLAGGED (outlier)" if r["flagged"] else ""
            print(
                f"  {r['node_id']}  |  "
                f"Temp: {r['temperature']:>8.2f}C  "
                f"Signal: {r['signal_strength']:>8.2f} dBm  "
                f"Alt: {r['altitude']:>8.2f} km"
                f"{flag}"
            )

        healthy = self.get_healthy_nodes(readings)
        offline = [s for s in self.satellites if not s.online]

        print("-" * 65)
        print(f"  Online  : {len(readings)}/{len(self.satellites)} satellites")
        print(f"  Healthy : {len(healthy)} nodes eligible for consensus")
        print(f"  Offline : {[s.node_id for s in offline]}")
        print(f"  Flagged : {[r['node_id'] for r in readings if r['flagged']]}")
        print("=" * 65)


#  Test 

if __name__ == "__main__":
    from satellite import create_default_satellites

    satellites = create_default_satellites()

    net = Network(satellites)

    # SAT-1 broadcasts to everyone
    print("\n-- SAT-1 broadcasting to network --\n")
    net.broadcast(satellites[0])

    # Show what messages were sent
    for msg in net.message_log:
        flag = " [FLAGGED]" if msg["flagged"] else ""
        print(f"  {msg['from']} --> {msg['to']}{flag}")

    # Full report
    print()
    net.get_status_report()