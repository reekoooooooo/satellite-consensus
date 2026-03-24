# Satellite Consensus Network Simulator

A Python simulation of a distributed satellite network that uses a simplified
version of the Raft consensus algorithm to agree on sensor data, handle failures,
and elect leaders — all visualized in real time with Matplotlib.

Built from scratch, stage by stage, with full explanations at every step.

---

## Table of Contents

1. [What Is This Project?](#what-is-this-project)
2. [Why Does Consensus Matter?](#why-does-consensus-matter)
3. [Real World Examples](#real-world-examples)
4. [Project Structure](#project-structure)
5. [File Breakdown](#file-breakdown)
6. [Libraries Used](#libraries-used)
7. [How To Run It](#how-to-run-it)
8. [Key Concepts Explained](#key-concepts-explained)
9. [What The Output Means](#what-the-output-means)
10. [Common Questions](#common-questions)

---

## What Is This Project?

Imagine 12 satellites orbiting Earth. Each one has sensors reading temperature,
signal strength, and altitude. They constantly send data back — but what happens
when two satellites report different readings for the same thing? What if one
satellite gets hit by a solar flare and starts sending garbage numbers? What if
one goes completely offline?

This project simulates exactly that scenario. The satellites communicate with
each other, vote to elect a trusted leader, and the leader locks in the agreed
correct values — automatically ignoring any satellite sending bad data or that
has gone offline.

That process of a group of nodes agreeing on one truth despite failures is called
**consensus**, and it is one of the most important concepts in distributed systems.

---

## Why Does Consensus Matter?

Any time you have multiple computers or devices that need to agree on something,
you need consensus. Without it, you get conflicting data, split decisions, and
systems that can't be trusted.

Think about it this way. You and four friends are deciding where to eat. One
friend says pizza, two say tacos, one says burgers, one doesn't respond because
their phone died. You hold a vote. Tacos wins. Everyone agrees and goes there —
even if it wasn't their first pick.

That is consensus. A group reaching one agreed decision even when not everyone
participates and not everyone agrees at first.

Now scale that to satellites orbiting at 17,000 miles per hour sending telemetry
data back to Earth every second, and you understand why this problem matters.

### The core problem consensus solves:

- Satellite A reads temperature as -40°C
- Satellite B reads temperature as -38°C
- Satellite C reads temperature as 700°C (sensor failure)

Without consensus: your ground station receives three different answers and has
no way to know which one to trust.

With consensus: the network votes, identifies that 700°C is clearly wrong,
excludes it, averages the two trusted readings, and commits -39°C as the agreed
truth. That agreed value is what gets logged and acted on.

---

## Real World Examples

### GPS
Your phone receives signals from multiple GPS satellites simultaneously. The
receiver runs its own form of consensus — if one satellite's timing signal looks
off compared to the others, it gets weighted lower or excluded entirely. That is
why GPS becomes more accurate the more satellites are in view.

### Starlink
SpaceX operates over 6,000 satellites in a mesh network. When a satellite reports
anomalous behavior, the constellation can detect the outlier and route around it
automatically. The inter-satellite links are constantly sharing telemetry and
cross-referencing readings.

### Military Satellite Communications
In contested environments, adversaries may attempt to jam or spoof satellite
signals. Consensus across multiple nodes allows the network to detect when one
node is behaving abnormally — whether due to hardware failure or external
interference — and isolate it without taking the whole network down.

### Deep Space Network
NASA's Deep Space Network uses multiple ground stations on different continents
to receive signals from deep space probes. Before acting on any single reading,
they cross-reference between stations. If one dish picks up something unexpected,
the others either confirm or contradict it. That cross-referencing is consensus.

---

## Project Structure

```
satellite-consensus/
│
├── satellite.py      Stage 1 — Defines what a satellite node is
├── network.py        Stage 2 — Handles communication between satellites
├── consensus.py      Stage 3 — Runs elections and commits agreed data
├── simulation.py     Stage 4 — Live simulation with random failures
└── visualizer.py     Stage 5 — Real time animated visualization
```

Each file has exactly one job. They build on top of each other like floors of a
building. You could swap out any one floor without touching the others.

---

## File Breakdown

### satellite.py — The Node

This file defines the blueprint for a single satellite. Think of it like a birth
certificate template. Every satellite created from this blueprint gets the same
attributes and abilities.

**What a satellite knows about itself:**

| Attribute        | What it means                                      |
|------------------|----------------------------------------------------|
| node_id          | Its name — SAT-1, SAT-2, etc                       |
| orbit_radius     | How far from Earth it flies                        |
| orbit_speed      | How fast it moves around the orbit                 |
| angle            | Where it currently is in the circle                |
| online           | Whether it is turned on                            |
| is_faulty        | Whether it is sending bad data                     |
| temperature      | Current temperature reading in Celsius             |
| signal_strength  | Current signal reading in dBm                      |
| altitude         | Current altitude reading in km                     |
| role             | follower, candidate, or leader                     |

**What a satellite can do:**

`update_position()` — moves the satellite a tiny bit each tick along its orbit,
like a clock hand advancing one second at a time.

`get_xy(cx, cy)` — converts the satellite's orbital angle into x and y screen
coordinates so the visualizer knows where to draw it.

`collect_sensor_data()` — generates sensor readings. Healthy satellites return
realistic values. Faulty satellites return wildly wrong values on purpose to
simulate real sensor failures.

```
Healthy satellite example:
  temperature:    -42.17°C
  signal_strength: -72.26 dBm
  altitude:        454.20 km

Faulty satellite example:
  temperature:    734.21°C    ← clearly wrong
  signal_strength: -189.50 dBm ← way out of range
  altitude:      88976.09 km  ← nowhere near real orbit
```

`create_default_satellites()` — a factory function that builds all 12 satellites
at once with pre-configured faults for testing. Any file that needs satellites
just calls this one function instead of building them manually every time.

---

### network.py — The Communication Layer

This file is the group chat system. It lets satellites send readings to each
other, timestamps every message, and automatically flags any satellite whose
numbers look suspicious.

**Key methods:**

`broadcast(sender)` — one satellite sends its current readings to every other
online satellite. Offline satellites get skipped automatically.

```
Example: SAT-1 broadcasts
  SAT-1 --> SAT-2
  SAT-1 --> SAT-4
  SAT-1 --> SAT-6
  (SAT-3 and SAT-5 are skipped — faulty and offline)
```

`is_outlier(data)` — the lie detector. Checks every reading against known normal
ranges. If anything falls outside the expected range, the whole reading gets
flagged as suspicious.

```
Normal ranges:
  temperature:     -90°C to 50°C
  signal_strength: -120 dBm to -30 dBm
  altitude:        300 km to 700 km

SAT-3 sends temperature: 629°C
  → 629 is above 50 → FLAGGED
```

`get_healthy_nodes()` — returns only the satellites that are online AND passing
the outlier check. This is the list that gets handed to consensus for voting.
Flagged satellites never make it to this list.

`get_status_report()` — prints a full dashboard showing who is healthy, who is
flagged, and who is offline.

---

### consensus.py — The Voting System

This is the brain. It takes the healthy node list from the network, runs an
election, picks a leader, and locks in the agreed sensor values. Based on a
simplified version of the Raft algorithm.

**The three roles:**

| Role      | What it means                                              |
|-----------|------------------------------------------------------------|
| leader    | Elected node that aggregates data and commits final values |
| follower  | Trusts the leader and contributes its readings             |
| candidate | Temporarily running for election                           |

**How an election works step by step:**

```
Step 1: Collect fresh readings from all satellites
Step 2: Run outlier detection — flag any suspicious nodes
Step 3: Build the eligible voter list — healthy nodes only
Step 4: Every eligible node becomes a candidate
Step 5: Every eligible node casts one vote for a random candidate
Step 6: Count votes — most votes wins
Step 7: If no majority — hold a revote (up to 3 times)
Step 8: Winner becomes leader, everyone else becomes follower
Step 9: Leader averages trusted readings and commits the result
```

**What a committed entry looks like:**

```
COMMITTED DATA — Term 2
─────────────────────────────────────────────────────────────────
  Leader         : SAT-4
  Trusted nodes  : ['SAT-1', 'SAT-2', 'SAT-4', 'SAT-6', 'SAT-7']
  Excluded nodes : ['SAT-3', 'SAT-8']
  Agreed values  :
    temperature          -34.05
    signal_strength      -70.58
    altitude             476.38
```

The agreed values are the average of every trusted node's reading. SAT-3 and
SAT-8 were caught by the outlier detector so their readings never touched the
average. The committed data is stored permanently in `committed_data[]` — an
append-only log of every truth the network has ever agreed on.

**What a term is:**

Every election cycle gets a term number. Term 1, Term 2, Term 3 and so on. This
number is like a season number. Every message and log entry gets tagged with it
so you always know which election it came from. If an old leader somehow comes
back online after being replaced, the term number lets the network know its
information is outdated.

**Majority voting and revotes:**

With 8 eligible voters, you need more than 4 votes to win — a strict majority.
If nobody hits that threshold on the first vote, a revote is held. Up to 3
revotes are allowed. If majority is still not achieved after that, the candidate
with the most votes wins by plurality.

```
Example with 8 voters (need >4 to win):

Round 1: SAT-1 gets 2, SAT-6 gets 3 → no majority, revote
Round 2: SAT-4 gets 3, SAT-2 gets 2 → no majority, revote
Round 3: SAT-7 gets 5 → majority achieved, SAT-7 wins
```

---

### simulation.py — The Live Fault Simulator

This file runs continuous election cycles with random failures injected between
each round. It is designed to prove that the network can survive chaos.

**Failure types:**

| Event         | What happens                              | Chance per round |
|---------------|-------------------------------------------|------------------|
| Goes offline  | Satellite stops responding entirely       | 15%              |
| Bad data      | Satellite starts sending out-of-range values | 10%           |
| Recovery      | Offline or faulty satellite returns to normal | 40%          |

These happen randomly each round before the election fires. The network has no
warning — it just adapts to whatever state the nodes are in when the vote starts.

**What a round looks like:**

```
SIMULATION ROUND 4 / 10

[ FAULT INJECTION ]
  ✔ SAT-1 came back ONLINE
  ✔ SAT-5 came back ONLINE
  ✘ SAT-8 went OFFLINE
  ✔ SAT-9 data normalized

NETWORK SNAPSHOT
  Healthy: 9  |  Faulty: 1  |  Offline: 2

ELECTION — TERM 4
  Eligible voters: ['SAT-1', 'SAT-2', 'SAT-3', ...]
  ... voting happens ...
  Winner: SAT-6

COMMITTED DATA — Term 4
  Agreed temperature: -27.35°C
  Agreed altitude:    466.25 km
```

---

### visualizer.py — The Live Dashboard

This file brings everything together into a real time animated window using
Matplotlib. It runs the full simulation — fault injection, elections, data
commits — and draws everything as it happens.

**What you see on screen:**

Left panel — the orbital view:
- 12 satellites orbiting Earth on a dark space background
- Each satellite color coded by current role
- Solar panel lines drawn on active satellites
- Green dashed beams flashing from leader to followers after each election
- Alert text appearing at the bottom when elections fire or failures happen
- Live frame counter and term number at the top

Right panel top — node telemetry:
- All 12 satellites listed with live updating sensor readings
- Status column showing current role for each node
- Color coded to match the orbital view

Right panel bottom — event log:
- Timestamped feed of every fault injection and election result
- Most recent event at the top, fades as events get older

**Role colors:**

| Color  | Role     |
|--------|----------|
| Green  | Leader   |
| Blue   | Follower |
| Red    | Faulty   |
| Grey   | Offline  |
| Yellow | Candidate (during voting) |

---

## Libraries Used

### random

### math

### time

### matplotlib
External library — requires install. The entire visualization is built with this.

```bash
pip install matplotlib
```

Key parts used:

`matplotlib.pyplot` — the main interface for creating figures and axes.

`matplotlib.animation.FuncAnimation` — calls your update function repeatedly
at a set interval, creating the animation effect.

`matplotlib.patches` — used to draw circles for Earth and the orbital glow
effects, and to create the legend color patches.

`plt.scatter` — draws all satellites as colored dots in one call.

---

## How To Run It

Make sure you are in the project folder first:

```bash
cd satellite-consensus
```

Install matplotlib if you have not already:

```bash
pip install matplotlib
```

Run each stage individually to see it build up:

```bash
python satellite.py     # Stage 1 — see satellite readings
python network.py       # Stage 2 — see network communication
python consensus.py     # Stage 3 — see elections and committed data
python simulation.py    # Stage 4 — see live fault simulation
python visualizer.py    # Stage 5 — see the full animated visualization
```

To run the visualizer maximize the window before your screen recording starts.
It looks significantly better fullscreen.

---

## Key Concepts Explained

### What is fault tolerance?
The system keeps working correctly even when parts of it break. In this project,
satellites can go offline or start sending bad data at any point. The network
detects the issue, excludes the broken node, and continues reaching consensus
with the remaining healthy nodes. It never crashes because of a single failure.

### What is redundancy?
Having more nodes than the minimum required so that failures do not cause the
whole system to go down. With 12 satellites and 4 starting as broken or offline,
8 healthy nodes still reach consensus every term. You could lose 5 more before
losing the ability to function.

### What is a quorum?
The minimum number of nodes needed to make a valid decision. In this project
that is a strict majority — more than half of the eligible voters. With 8 voters
you need at least 5. With 4 voters you need at least 3. Elections below quorum
trigger revotes.

### What is the difference between faulty and offline?
An offline satellite is completely silent. It sends nothing. The network ignores
it entirely because it does not respond. A faulty satellite is still transmitting
but sending wrong data — it is the more dangerous of the two because it looks
active but is lying. The outlier detector in network.py catches faulty satellites
by checking their readings against known normal ranges.

### Why does the leader change each term?
Because voting is randomized. Each eligible satellite votes for a random
candidate, so different nodes win different terms. In a real implementation
leadership might be influenced by signal quality, orbital position, remaining
power, or connection stability. Randomized voting here simulates the natural
variation you would see in a real constellation.

---

## What The Output Means

### Network snapshot
```
Healthy: 9  |  Faulty: 1  |  Offline: 2
```
9 satellites are sending clean data and eligible to vote. 1 is sending bad data
and will be excluded. 2 are completely silent.

### Election output
```
Eligible voters : ['SAT-2', 'SAT-4', 'SAT-5', 'SAT-6']
SAT-2 votes for SAT-4
SAT-4 votes for SAT-4
SAT-5 votes for SAT-2
SAT-6 votes for SAT-5
Winner : SAT-4 with 2 vote(s)
```
Only the healthy nodes appear as eligible voters. Each one casts exactly one
vote. SAT-4 got two votes and won that term.

### Committed data
```
Agreed values:
  temperature      -34.05
  signal_strength  -70.58
  altitude         476.38
```
These are the averages of every trusted node's reading for that term. This is
the single agreed truth the network has committed to for term 2. It goes into
permanent storage and cannot be changed.

### Fault event log
```
x  SAT-6 went OFFLINE       - something broke
warning  SAT-9 started BAD DATA   - sensor failure detected
check  SAT-3 came back ONLINE   - recovered
```
These events happen randomly between election rounds. The symbols make it easy
to scan quickly — X for failures, warning for bad data, checkmark for recovery.

---

## Common Questions

**Why does the leader sometimes change even when nothing broke?**
Because votes are randomized. Any healthy satellite can win any election. This
is intentional — it simulates the natural variation in a real constellation
where leadership might shift based on orbital position or signal quality.

**Why does it sometimes take multiple revotes?**
With many voters and purely random voting, the votes spread out across many
candidates. Hitting a strict majority by chance takes longer with more voters.
With 10 eligible voters you need 6 votes to win, which with random voting often
takes a few rounds to concentrate enough on one candidate.

**What happens if all satellites go offline?**
The election returns None, no data is committed for that term, and the system
waits for the next round to try again. It does not crash. This is the graceful
degradation part of fault tolerance.

---

## Summary

This project demonstrates distributed systems concepts in a visible and
understandable way. It covers:

- Object oriented design with a clean class hierarchy
- Network communication and message passing between nodes
- Outlier detection and data validation
- Leader election with majority voting and revotes
- Fault injection and live recovery
- Real time data visualization

The same core concepts appear in GPS constellations, satellite mesh networks,
military communication systems, cloud infrastructure, and blockchain networks.
Building it from scratch gives you the mental model to understand all of them.
