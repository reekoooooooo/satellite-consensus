# Satellite Consensus Deep Dive

## Purpose
This document expands the current simulation from three basic layers into a mission-grade consensus framework suitable for constellation operations under delay, faults, and partitions.

## Current State in This Project
Your codebase already models important foundations:
- Data consensus: outlier filtering and trusted node selection in network.py
- Leadership consensus: majority election with revote in consensus.py
- Dynamic faults: offline and faulty transitions in simulation.py and visualizer.py

The next maturity jump is control consensus: agreement on operational actions, not just agreement on state.

---

## Layer Model (Operational View)

### Layer 1: Data Consensus (What is true?)
Goal:
- Detect bad telemetry and prevent it from contaminating decisions.

Current implementation:
- Threshold-based outlier detection by metric (temperature, signal strength, altitude).

Gaps to close:
- Static thresholds can be fragile across mission phases.
- No confidence score per measurement.

Recommended upgrade:
- Replace hard threshold-only logic with hybrid scoring:
  - Physical limits (hard reject)
  - Statistical anomaly score (soft reject)
  - Temporal consistency score (drift check)
- Produce per-node trust_score in range [0, 1].

---

### Layer 2: Leadership Consensus (Who decides?)
Goal:
- Keep exactly one active leader for each healthy quorum.

Current implementation:
- Majority election with limited revotes and emergency re-election in visualizer path.

Gaps to close:
- No explicit network partition model.
- No delayed message handling.

Recommended upgrade:
- Introduce election timeout windows and heartbeat leases.
- Track leader lease expiry and require renewal before command authority.

---

### Layer 3: Control Consensus (What action is authorized?)
Goal:
- Approve mission actions based on risk class and quorum policy.

Current implementation:
- Not yet present.

Recommended upgrade:
- Add command proposals and commit flow:
  1) propose action
  2) validate constraints
  3) vote with weighted trust
  4) commit only if policy threshold met
  5) audit log action

---

## Real-World Constraints to Model

### 1) Time, Delay, and Clock Drift
Why this matters:
- Consensus depends on ordering and deadlines.
- Delayed votes can create split outcomes if accepted late.

Model additions:
- Every message includes:
  - sent_at
  - received_at
  - expires_at
  - term
- Reject if now > expires_at.
- Reject if message.term < current_term.

Simulation target values:
- Intra-LEO link delay: 20 to 80 ms
- Sat-ground delay: 250 to 600 ms

Implementation note:
- In frame-based simulation, represent delay in frame offsets.

---

### 2) Quorum Under Partitions (Anti Split-Brain)
Why this matters:
- Two partitioned groups can elect conflicting leaders.

Policy:
- Only component with strict majority of total voting weight can commit.
- Minority component enters degraded mode and does not commit control commands.

State machine suggestion:
- normal
- partitioned_majority
- partitioned_minority
- rejoin_reconcile

Reconciliation rule:
- On heal, keep longest valid committed log with highest term and valid quorum proofs.

---

### 3) Weighted Trust Voting
Why this matters:
- One-node-one-vote ignores health quality.

Base model:
- effective_vote = base_weight * trust_score * role_factor

Example components:
- base_weight: static capability weight (power, antenna quality)
- trust_score: dynamic quality from recent telemetry behavior
- role_factor: optional operational modifier

Suggested trust decay:
- trust_score(t+1) = clamp(trust_score(t) - penalty + recovery, 0, 1)

Penalties:
- outlier spike
- repeated near-threshold anomalies
- message delivery failures

---

### 4) Byzantine Fault Tolerance Inputs
Why this matters:
- Smart adversaries can send plausible but conflicting data.

Minimum security controls:
- Message signatures per node key
- Monotonic nonce per sender
- Term-bound vote IDs
- Equivocation detector

Equivocation rule:
- If same node signs two different votes for same term and same election_id, slash trust_score and quarantine candidate influence.

Replay protection:
- Keep nonce window per sender.
- Reject duplicate or stale nonces.

---

### 5) Safety Envelopes and Decision Classes
Why this matters:
- Different actions have different mission risk.

Suggested policy table:
- telemetry_commit: threshold > 50%
- antenna_retune: threshold >= 66%
- slot_adjustment: threshold >= 75%
- collision_avoidance: threshold 100% or ground override

Each command should include:
- command_id
- action_type
- risk_class
- validity_window
- required_threshold
- constraint_hash

Constraint hash idea:
- Hash of pre-check results so voters approve the same validated plan.

---

### 6) Mission-Coupled Leader Utility
Why this matters:
- Some leaders are operationally better than others.

Leader utility score example:
- utility = a*coverage + b*power_margin + c*thermal_headroom + d*link_quality - e*fuel_cost

Election tie-break:
- If vote tie, prefer higher utility score.

Operational benefit:
- Better mission throughput while preserving consensus correctness.

---

## Recommended Architecture Update

### Core Objects to Add
- Message:
  - id, sender, recipient, term, type, payload, sent_at, expires_at, nonce, signature
- NodeHealth:
  - trust_score, anomaly_count, delivery_success_rate, thermal_state, power_margin
- CommandProposal:
  - command_id, action_type, params, risk_class, required_threshold, proposer, created_at
- CommitRecord:
  - term, leader, proposal_id, voter_set, weighted_quorum, proof_hash

### New Modules (Proposed)
- timing.py: delay, clock drift, expiry checks
- trust.py: trust score update rules
- protocol.py: signed message schema and nonce validation
- control.py: proposal, vote, commit pipeline
- partition.py: topology partition detection and quorum mode transitions

---

## Implementation Roadmap for This Repository

### Phase 1: Deterministic Timing and Message Validity
- Add logical clock and message queue with delivery delay.
- Add expires_at and stale term rejection to election messages.
- Add reproducible random seeds for scenario replay.

### Phase 2: Partition-Aware Election
- Simulate communication graph per round/frame.
- Elect only in components with valid quorum.
- Add minority-safe mode and no-commit guardrails.

### Phase 3: Trust-Weighted Voting
- Compute trust_score from telemetry quality and protocol behavior.
- Convert election from integer vote counts to weighted totals.
- Log trust transitions in event logs.

### Phase 4: Control Consensus
- Implement command proposal object and class-based thresholds.
- Add commit proof records and audit output.
- Add failure injection for command conflicts.

### Phase 5: Byzantine Scenario Pack
- Add equivocation and replay attack simulators.
- Add signature and nonce checks.
- Validate that bad actors cannot force incorrect commits.

---

## Validation and Metrics

Track these metrics every term:
- leader_stability: term duration before forced re-election
- consensus_latency_ms: proposal to commit latency
- stale_message_reject_rate
- partition_safety_violations (must remain zero)
- false_accept_rate for outlier data
- command_commit_success_by_risk_class

Acceptance criteria examples:
- No dual commits across partitions in 10,000 simulated terms
- All stale term messages rejected
- Collision avoidance commands never commit below configured threshold

---

## Suggested Near-Term Enhancements for Your Existing Files

- network.py:
  - Add measurement confidence and trust outputs, not only flagged boolean.
- consensus.py:
  - Introduce weighted quorum and vote expiry checks.
- simulation.py:
  - Add partition scenarios and delayed message queues.
- visualizer.py:
  - Add separate panels for trust scores and quorum component size.

---

## Example Control Consensus Flow

1) Leader proposes antenna retune with risk_class=medium and threshold=0.66.
2) Nodes verify constraints and timestamp validity.
3) Nodes cast signed votes with nonce.
4) Protocol verifies signature, term, nonce, and expiry.
5) Weighted quorum reaches threshold.
6) Commit record is appended with proof hash.
7) Execution ack is logged; rollback path is armed if post-check fails.

---

## Final Takeaway
You already have a strong prototype for Layers 1 and 2. The highest value next step is Layer 3 with strict policy-driven control consensus. Once command classes, weighted quorum, and partition-safe commit rules are in place, this moves from a good simulation to an architecture that resembles operational satellite autonomy.
