import time
import random
from satellite import create_default_satellites
from network import Network
from consensus import RaftConsensus


#  Config 
ELECTION_INTERVAL   = 3.0   # seconds between elections
FAILURE_CHANCE      = 0.15  # 15% chance a satellite breaks each round
RECOVERY_CHANCE     = 0.40  # 40% chance a broken satellite recovers each round
FAULT_CHANCE        = 0.10  # 10% chance a satellite starts sending bad data
TOTAL_ROUNDS        = 10    # how many election cycles to simulate 


class Simulation:
    def __init__(self):
        self.satellites = create_default_satellites()
        self.network    = Network(self.satellites)
        self.raft       = RaftConsensus(self.network)
        self.round      = 0
        self.event_log  = []   # every failure and recovery gets logged here

    #  Failure Injection 

    def inject_failures(self):
        """
        Randomly break satellites each round.
        Each online healthy satellite has a small chance to:
          - go offline completely
          - start sending faulty data
        Each broken satellite has a chance to recover.
        """
        events = []

        for sat in self.satellites:
            # Recovery first — give broken sats a chance to come back
            if not sat.online:
                if random.random() < RECOVERY_CHANCE:
                    sat.online    = True
                    sat.is_faulty = False
                    events.append(f"  [RECOVER]  {sat.node_id} came back ONLINE")

            elif sat.is_faulty:
                if random.random() < RECOVERY_CHANCE:
                    sat.is_faulty = False
                    events.append(f"  [RECOVER]  {sat.node_id} data normalized - fault cleared")

            else:
                # Healthy sat — small chance something goes wrong
                roll = random.random()
                if roll < FAILURE_CHANCE:
                    sat.online = False
                    events.append(f"  [FAIL]     {sat.node_id} went OFFLINE")
                elif roll < FAILURE_CHANCE + FAULT_CHANCE:
                    sat.is_faulty = True
                    events.append(f"  [WARN]     {sat.node_id} started sending BAD DATA")

        if events:
            print(f"\n  [ FAULT INJECTION — Round {self.round} ]")
            for e in events:
                print(e)
            self.event_log.extend(events)
        else:
            print(f"\n  [ No failures this round ]")

    #  Round Summary 

    def print_round_header(self):
        print(f"\n\n{'#' * 65}")
        print(f"  SIMULATION ROUND {self.round} / {TOTAL_ROUNDS}")
        print(f"{'#' * 65}")

    def print_network_snapshot(self):
        """Quick one-line status for every satellite."""
        print(f"\n  NETWORK SNAPSHOT")
        print(f"  {'─' * 60}")
        online  = 0
        faulty  = 0
        offline = 0
        for sat in self.satellites:
            if not sat.online:
                offline += 1
            elif sat.is_faulty:
                faulty += 1
            else:
                online += 1
            print(f"  {sat.status()}")
        print(f"  {'─' * 60}")
        print(f"  Healthy: {online}  |  Faulty: {faulty}  |  Offline: {offline}")

    #  Main Loop 

    def run(self):
        print("=" * 65)
        print("  SATELLITE CONSENSUS NETWORK — LIVE SIMULATION")
        print(f"  {TOTAL_ROUNDS} rounds  |  {ELECTION_INTERVAL}s interval  |  12 satellites")
        print("=" * 65)

        for _ in range(TOTAL_ROUNDS):
            self.round += 1
            self.print_round_header()

            # Step 1: Inject random failures and recoveries
            self.inject_failures()

            # Step 2: Show current network state
            self.print_network_snapshot()

            # Step 3: Run election — may fail if too many nodes are down
            winner = self.raft.start_election()

            # Step 4: If election succeeded commit the data
            if winner:
                entry = self.raft.commit_readings()
                self.raft.print_commit(entry)
            else:
                print("\n  Election failed — not enough healthy nodes.")
                print("  Network is degraded. Waiting for recovery...")

            # Step 5: Wait before next round
            if self.round < TOTAL_ROUNDS:
                print(f"\n  ... waiting {ELECTION_INTERVAL}s for next round ...")
                time.sleep(ELECTION_INTERVAL)

        #  Final Report 
        self.print_final_report()

    #  Final Report 

    def print_final_report(self):
        print(f"\n\n{'=' * 65}")
        print("  SIMULATION COMPLETE — FINAL REPORT")
        print(f"{'=' * 65}")

        # Election history
        self.raft.print_election_history()

        # Committed data summary
        print(f"\n  COMMITTED DATA SUMMARY")
        print(f"  {'─' * 60}")
        if not self.raft.committed_data:
            print("  No data was committed.")
        else:
            for entry in self.raft.committed_data:
                v = entry["agreed_values"]
                print(
                    f"  Term {entry['term']:<4} | "
                    f"Leader: {entry['leader']:<8} | "
                    f"Temp: {v['temperature']:>7.2f}C | "
                    f"Signal: {v['signal_strength']:>7.2f} dBm | "
                    f"Alt: {v['altitude']:>7.2f} km"
                )

        # Event log — all failures and recoveries
        print(f"\n  FAULT EVENT LOG")
        print(f"  {'─' * 60}")
        if not self.event_log:
            print("  No faults occurred.")
        else:
            for event in self.event_log:
                print(f" {event}")

        # Final node states
        print(f"\n  FINAL NODE STATES")
        print(f"  {'─' * 60}")
        for sat in self.satellites:
            print(f"  {sat.status()}")

        print(f"\n{'=' * 65}")
        print("  END OF SIMULATION")
        print(f"{'=' * 65}\n")


#  Entry Point 

if __name__ == "__main__":
    sim = Simulation()
    sim.run()