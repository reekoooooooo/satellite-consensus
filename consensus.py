import random
import time
from satellite import create_default_satellites
from network import Network


class RaftConsensus:
    """
    Simplified Raft consensus algorithm.
    Healthy satellites vote to elect one leader.
    The leader aggregates trusted readings from all followers.
    Faulty and offline nodes are excluded from the vote.
    """

    def __init__(self, network):
        self.network        = network
        self.satellites     = network.satellites
        self.term           = 0          # Election round number
        self.leader         = None       # Current leader satellite
        self.election_log   = []         # History of all elections
        self.committed_data = []         # Agreed upon data entries

    #  Election 

    def start_election(self):
        """Run one full election cycle with majority voting and revote if needed."""
        self.term += 1
        print(f"\n{'=' * 65}")
        print(f"  ELECTION — TERM {self.term}")
        print(f"{'=' * 65}")

        # Step 1: Get only healthy nodes — faulty and offline can't vote
        readings        = self.network.collect_all_readings()
        eligible_voters = self.network.get_healthy_nodes(readings)

        if not eligible_voters:
            print("  No eligible voters. Election failed.")
            return None

        print(f"  Eligible voters : {[s.node_id for s in eligible_voters]}")
        majority_threshold = len(eligible_voters) / 2.0
        revote_count = 0
        max_revotes = 3

        while revote_count <= max_revotes:
            if revote_count > 0:
                print(f"\n  REVOTE {revote_count} (no majority achieved)\n")
            
            # Step 2: Each eligible satellite nominates itself as candidate
            for sat in eligible_voters:
                sat.role           = "candidate"
                sat.votes_received = 0

            # Step 3: Each voter casts one vote for a random candidate
            for voter in eligible_voters:
                candidate = random.choice(eligible_voters)
                candidate.votes_received += 1
                print(f"  {voter.node_id} votes for {candidate.node_id}")

            # Step 4: Candidate with most votes
            winner = max(eligible_voters, key=lambda s: s.votes_received)
            print(f"\n  Top candidate: {winner.node_id} with {winner.votes_received} vote(s) (need >{majority_threshold:.0f})")

            # Step 5: Check if majority achieved
            if winner.votes_received > majority_threshold:
                break  # We have a winner
            
            revote_count += 1

        # Step 6: Assign roles
        for sat in self.satellites:
            if not sat.online:
                sat.role = "offline"
            elif sat.is_faulty:
                sat.role = "faulty"
            elif sat.node_id == winner.node_id:
                sat.role           = "leader"
                sat.current_leader = winner.node_id
            else:
                sat.role           = "follower"
                sat.current_leader = winner.node_id

        self.leader = winner

        print(f"\n  Winner : {winner.node_id} with {winner.votes_received} vote(s)")
        print(f"  Term   : {self.term}")

        # Log the result
        self.election_log.append({
            "term":       self.term,
            "leader":     winner.node_id,
            "votes":      winner.votes_received,
            "voters":     [s.node_id for s in eligible_voters],
            "revotes":    revote_count,
            "timestamp":  time.time(),
        })

        return winner

    #  Data Aggregation 

    def commit_readings(self):
        """
        Leader collects readings from all followers and
        computes the agreed average for each sensor.
        Faulty and offline nodes are excluded.
        """
        if not self.leader:
            print("  No leader elected yet. Run start_election() first.")
            return None

        readings = self.network.collect_all_readings()
        trusted  = [r for r in readings if not r["flagged"]]

        if not trusted:
            print("  No trusted readings to commit.")
            return None

        # Average the trusted values
        avg_temp     = sum(r["temperature"]     for r in trusted) / len(trusted)
        avg_signal   = sum(r["signal_strength"] for r in trusted) / len(trusted)
        avg_altitude = sum(r["altitude"]        for r in trusted) / len(trusted)

        entry = {
            "term":            self.term,
            "leader":          self.leader.node_id,
            "trusted_nodes":   [r["node_id"] for r in trusted],
            "excluded_nodes":  [r["node_id"] for r in readings if r["flagged"]],
            "agreed_values": {
                "temperature":     round(avg_temp, 2),
                "signal_strength": round(avg_signal, 2),
                "altitude":        round(avg_altitude, 2),
            },
            "timestamp": time.time(),
        }

        self.committed_data.append(entry)
        return entry

    #  Display 

    def print_commit(self, entry):
        """Pretty print a committed data entry."""
        if not entry:
            return
        print(f"\n{'─' * 65}")
        print(f"  COMMITTED DATA — Term {entry['term']}")
        print(f"{'─' * 65}")
        print(f"  Leader         : {entry['leader']}")
        print(f"  Trusted nodes  : {entry['trusted_nodes']}")
        print(f"  Excluded nodes : {entry['excluded_nodes']}")
        print(f"  Agreed values  :")
        for key, val in entry["agreed_values"].items():
            print(f"    {key:<20} {val}")
        print(f"{'─' * 65}")

    def print_election_history(self):
        """Print a summary of all elections that have occurred."""
        print(f"\n{'=' * 65}")
        print("  ELECTION HISTORY")
        print(f"{'=' * 65}")
        for e in self.election_log:
            revotes = e.get('revotes', 0)
            print(
                f"  Term {e['term']:<4} | "
                f"Leader: {e['leader']:<8} | "
                f"Votes: {e['votes']:<3} | "
                f"Revotes: {revotes:<2} | "
                f"Voters: {len(e['voters'])}"
            )
        print(f"{'=' * 65}")


#  Test 

if __name__ == "__main__":
    satellites = create_default_satellites()
    net        = Network(satellites)
    raft       = RaftConsensus(net)

    # Run 5 elections to show leadership can change
    for _ in range(5):
        raft.start_election()
        entry = raft.commit_readings()
        raft.print_commit(entry)

    # Full role summary
    print("\n  FINAL NODE ROLES")
    print(f"{'─' * 65}")
    for sat in satellites:
        print(sat.status())

    # Election history
    raft.print_election_history()