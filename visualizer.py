import math
import random
from datetime import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation
from satellite import create_default_satellites
from network import Network
from consensus import RaftConsensus

# ── Layout Config ────────────────────────────────────────────
ORBIT_RADIUS     = 2.8      # orbital radius in plot units
EARTH_RADIUS     = 0.55     # earth circle size
FPS              = 24       # lower FPS keeps UI smoother on slower machines
TERM_SECONDS     = 4.0      # seconds per election term
ELECTION_EVERY   = int(TERM_SECONDS * FPS)
FAULT_EVERY      = 90       # frames between random fault injections
ORBIT_SPEED      = 0.012    # radians per frame
FAILURE_CHANCE   = 0.18
RECOVERY_CHANCE  = 0.40
FAULT_CHANCE     = 0.10
MIN_SATELLITES   = 4
LOG_FILE_PREFIX  = "event_log"

# ── Role Colors ──────────────────────────────────────────────
ROLE_COLORS = {
    "leader":   "#00ff99",
    "follower": "#4da6ff",
    "faulty":   "#ff4d6d",
    "offline":  "#555566",
    "candidate":"#ffdd00",
}

ROLE_SIZES = {
    "leader":   220,
    "follower": 120,
    "faulty":   130,
    "offline":  80,
    "candidate":160,
}


class SatelliteVisualizer:
    def __init__(self):
        # ── Data setup ───────────────────────────────────────
        self.satellites  = create_default_satellites()
        self.network     = Network(self.satellites)
        self.raft        = RaftConsensus(self.network)
        self.frame       = 0
        self.alerts      = []       # [(message, expiry_frame, color)]
        self.beam_pairs  = []       # [(leader_idx, follower_idx, expiry)]
        self.event_log   = []       # rolling list of recent events
        self.ani         = None
        self.legend_artist = None
        self.next_sat_id = len(self.satellites) + 1
        self.log_file_path = ""

        # Spread satellites evenly around orbit to start
        n = len(self.satellites)
        for i, sat in enumerate(self.satellites):
            sat.angle = (i / n) * 2 * math.pi
            sat.orbit_speed = ORBIT_SPEED + i * 0.0005

        # ── Figure setup ─────────────────────────────────────
        plt.style.use("dark_background")
        self.fig = plt.figure(figsize=(16, 9), facecolor="#050a14")
        self.fig.canvas.manager.set_window_title(
            "Satellite Consensus Network — Live Simulation"
        )
        self.fig.canvas.mpl_connect("key_press_event", self._on_key_press)

        # Main orbital view — left 60%
        self.ax_orbit = self.fig.add_axes([0.01, 0.01, 0.58, 0.98])
        self.ax_orbit.set_facecolor("#050a14")
        self.ax_orbit.set_xlim(-5, 5)
        self.ax_orbit.set_ylim(-5, 5)
        self.ax_orbit.set_aspect("equal")
        self.ax_orbit.axis("off")

        # Data panel — top right
        self.ax_data = self.fig.add_axes([0.61, 0.38, 0.38, 0.60])
        self.ax_data.set_facecolor("#080d1a")
        self.ax_data.axis("off")

        # Event log — bottom right
        self.ax_log = self.fig.add_axes([0.61, 0.01, 0.38, 0.35])
        self.ax_log.set_facecolor("#080d1a")
        self.ax_log.axis("off")

        # Create a unique per-run log file with date and time in the name.
        run_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file_path = f"{LOG_FILE_PREFIX}_{run_stamp}.txt"
        with open(self.log_file_path, "w", encoding="utf-8") as f:
            f.write("Satellite Visualizer Event Log\n")
            f.write("frame,event\n")

        self._draw_static_elements()

    # ── Static Background ────────────────────────────────────

    def _draw_static_elements(self):
        ax = self.ax_orbit

        # Stars
        rng = random.Random(42)
        for _ in range(140):
            x = rng.uniform(-5, 5)
            y = rng.uniform(-5, 5)
            s = rng.choice([1, 1, 1, 2, 3])
            ax.plot(x, y, "o", color="white",
                    markersize=s * 0.4,
                    alpha=rng.uniform(0.2, 0.9), zorder=1)

        # Orbit ring
        theta = [i * 2 * math.pi / 360 for i in range(361)]
        ox = [ORBIT_RADIUS * math.cos(t) for t in theta]
        oy = [ORBIT_RADIUS * math.sin(t) for t in theta]
        ax.plot(ox, oy, color="#1a2a44", linewidth=0.8,
                linestyle="--", zorder=2, alpha=0.6)

        # Grid rings (faint)
        for r in [1.5, 2.0, 3.5, 4.2]:
            gx = [r * math.cos(t) for t in theta]
            gy = [r * math.sin(t) for t in theta]
            ax.plot(gx, gy, color="#0d1a2e", linewidth=0.4,
                    zorder=1, alpha=0.4)

        # Earth glow
        for r, alpha in [(0.80, 0.04), (0.68, 0.07), (0.60, 0.12)]:
            glow = plt.Circle((0, 0), r, color="#4da6ff",
                               zorder=3, alpha=alpha)
            ax.add_patch(glow)

        # Earth body
        earth = plt.Circle((0, 0), EARTH_RADIUS,
                            color="#0d3d5c", zorder=4)
        ax.add_patch(earth)
        earth_border = plt.Circle((0, 0), EARTH_RADIUS,
                                   fill=False, edgecolor="#1e6090",
                                   linewidth=1.5, zorder=5)
        ax.add_patch(earth_border)
        ax.text(0, 0, "EARTH", ha="center", va="center",
                color="#4da6ff", fontsize=7, fontweight="bold",
                fontfamily="monospace", zorder=6)

        # Panel borders
        for ax_p in [self.ax_data, self.ax_log]:
            for spine in ax_p.spines.values():
                spine.set_edgecolor("#1a2a44")
                spine.set_linewidth(1)

        # Panel titles
        self.ax_data.text(0.5, 0.97, "NODE TELEMETRY",
                          transform=self.ax_data.transAxes,
                          ha="center", va="top", color="#4da6ff",
                          fontsize=9, fontfamily="monospace",
                          fontweight="bold", alpha=0.8)

        self.ax_log.text(0.5, 0.97, "EVENT LOG",
                         transform=self.ax_log.transAxes,
                         ha="center", va="top", color="#4da6ff",
                         fontsize=9, fontfamily="monospace",
                         fontweight="bold", alpha=0.8)

    # ── Fault Injection ──────────────────────────────────────

    def _inject_faults(self):
        for sat in self.satellites:
            if not sat.online:
                if random.random() < RECOVERY_CHANCE:
                    sat.online    = True
                    sat.is_faulty = False
                    self._add_event(f"✔ {sat.node_id} back ONLINE", "#00ff99")
            elif sat.is_faulty:
                if random.random() < RECOVERY_CHANCE:
                    sat.is_faulty = False
                    self._add_event(f"✔ {sat.node_id} data normalized", "#00ff99")
            else:
                roll = random.random()
                if roll < FAILURE_CHANCE:
                    sat.online = False
                    self._add_event(f"✘ {sat.node_id} went OFFLINE", "#ff4d6d")
                elif roll < FAILURE_CHANCE + FAULT_CHANCE:
                    sat.is_faulty = True
                    self._add_event(f"⚠ {sat.node_id} BAD DATA", "#ffaa00")

    def _get_active_leader(self):
        """Return current leader only if that node is still healthy and online."""
        leader = self.raft.leader
        if leader and leader.online and not leader.is_faulty:
            return leader
        return None

    # ── Election ─────────────────────────────────────────────

    def _run_election(self):
        winner = self.raft.start_election()
        if winner:
            self._add_alert(
                f"★  TERM {self.raft.term}  —  LEADER: {winner.node_id}",
                expiry=self.frame + 90,
                color="#00ff99",
            )
            self._add_event(
                f"★ Term {self.raft.term}: {winner.node_id} elected leader",
                "#00ff99",
            )
            # Draw beams from leader to followers
            leader_idx = next(
                (i for i, s in enumerate(self.satellites)
                 if s.node_id == winner.node_id), None
            )
            if leader_idx is not None:
                for i, sat in enumerate(self.satellites):
                    if sat.role == "follower":
                        self.beam_pairs.append(
                            (leader_idx, i, self.frame + 45)
                        )
        else:
            self.raft.leader = None
            self._add_alert(
                "⚠  ELECTION FAILED — NOT ENOUGH NODES",
                expiry=self.frame + 90,
                color="#ff4d6d",
            )

    # ── Alerts & Events ──────────────────────────────────────

    def _add_alert(self, msg, expiry, color="#ffffff"):
        self.alerts.append({"msg": msg, "expiry": expiry, "color": color})

    def _add_event(self, msg, color="#c8d8f0"):
        ts = f"T{self.frame:05d}"
        self.event_log.insert(0, {"ts": ts, "msg": msg, "color": color})
        self.event_log = self.event_log[:14]   # keep last 14 events
        wall_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(f"{self.frame},{wall_time},{msg}\n")

    def _rebalance_orbits(self):
        """Re-space satellites evenly after add/remove operations."""
        n = len(self.satellites)
        if n == 0:
            return
        for i, sat in enumerate(self.satellites):
            sat.angle = (i / n) * 2 * math.pi
            sat.orbit_speed = ORBIT_SPEED + i * 0.0005

    def _add_satellite(self):
        from satellite import Satellite

        sat = Satellite(
            f"SAT-{self.next_sat_id}",
            orbit_radius=200,
            orbit_speed=ORBIT_SPEED,
        )
        self.next_sat_id += 1
        self.satellites.append(sat)
        self._rebalance_orbits()
        self._add_event(f"+ Added {sat.node_id}", "#4da6ff")

    def _remove_satellite(self):
        if len(self.satellites) <= MIN_SATELLITES:
            self._add_event("! Minimum satellite count reached", "#ffaa00")
            return

        removed = self.satellites.pop()
        if self.raft.leader and self.raft.leader.node_id == removed.node_id:
            self.raft.leader = None
            self._add_event(f"- Removed leader {removed.node_id}", "#ff4d6d")
        else:
            self._add_event(f"- Removed {removed.node_id}", "#ff4d6d")

        self._rebalance_orbits()

    def _on_key_press(self, event):
        key = (event.key or "").lower()
        if key in {"+", "="}:
            self._add_satellite()
        elif key == "-":
            self._remove_satellite()

    # ── Animation Frame ──────────────────────────────────────

    def update(self, frame_num):
        self.frame = frame_num

        # Move satellites
        for sat in self.satellites:
            sat.angle = (sat.angle + sat.orbit_speed) % (2 * math.pi)
            sat.collect_sensor_data()

        # Trigger fault injection
        if frame_num % FAULT_EVERY == 0 and frame_num > 0:
            leader_before_faults = self._get_active_leader()
            self._inject_faults()
            if leader_before_faults and self._get_active_leader() is None:
                self._add_event(
                    f"⚠ Leader {leader_before_faults.node_id} became unavailable",
                    "#ffaa00",
                )

        # Trigger election
        if frame_num % ELECTION_EVERY == 0:
            self._run_election()
        elif self._get_active_leader() is None and frame_num % 30 == 0:
            # Fast recovery when leader is lost between scheduled elections.
            self._add_event("↻ Emergency election triggered", "#ffaa00")
            self._run_election()

        # Clear dynamic artists
        for coll in list(self.ax_orbit.collections):
            if coll.get_gid() == "dynamic":
                coll.remove()
        for txt in list(self.ax_orbit.texts):
            if txt.get_gid() == "dynamic":
                txt.remove()
        for line in list(self.ax_orbit.lines[4:]):  # keep orbit ring + grid lines
            if line.get_gid() == "dynamic":
                line.remove()
        self.ax_data.clear()
        self.ax_data.axis("off")
        self.ax_log.clear()
        self.ax_log.axis("off")

        self._draw_beams(frame_num)
        self._draw_satellites()
        self._draw_alerts(frame_num)
        self._draw_data_panel()
        self._draw_event_log()
        self._draw_header(frame_num)

        return []

    # ── Draw Beams ───────────────────────────────────────────

    def _draw_beams(self, frame_num):
        active = []
        for (li, fi, expiry) in self.beam_pairs:
            if frame_num <= expiry:
                active.append((li, fi, expiry))
                lx = ORBIT_RADIUS * math.cos(self.satellites[li].angle)
                ly = ORBIT_RADIUS * math.sin(self.satellites[li].angle)
                fx = ORBIT_RADIUS * math.cos(self.satellites[fi].angle)
                fy = ORBIT_RADIUS * math.sin(self.satellites[fi].angle)
                alpha = max(0.1, (expiry - frame_num) / 45)
                (beam_line,) = self.ax_orbit.plot(
                    [lx, fx], [ly, fy],
                    color="#00ff99", linewidth=0.8,
                    alpha=alpha * 0.7, zorder=6,
                    linestyle="--"
                )
                beam_line.set_gid("dynamic")
        self.beam_pairs = active

    # ── Draw Satellites ──────────────────────────────────────

    def _draw_satellites(self):
        ax = self.ax_orbit
        xs, ys, colors, sizes, zorders = [], [], [], [], []

        for sat in self.satellites:
            x = ORBIT_RADIUS * math.cos(sat.angle)
            y = ORBIT_RADIUS * math.sin(sat.angle)

            role = sat.role if sat.online else "offline"
            if sat.is_faulty and sat.online:
                role = "faulty"

            color  = ROLE_COLORS.get(role, "#888888")
            size   = ROLE_SIZES.get(role, 100)

            xs.append(x)
            ys.append(y)
            colors.append(color)
            sizes.append(size)

            # Satellite label
            offset = 0.38
            sat_label = ax.text(
                x + offset * math.cos(sat.angle),
                y + offset * math.sin(sat.angle),
                sat.node_id,
                color=color, fontsize=6.5,
                fontfamily="monospace",
                ha="center", va="center",
                zorder=10, fontweight="bold",
                alpha=0.95,
            )
            sat_label.set_gid("dynamic")

            # Leader crown marker
            if role == "leader":
                crown = ax.text(
                    x, y + 0.26, "★",
                    color="#00ff99", fontsize=9,
                    ha="center", va="center",
                    zorder=11,
                )
                crown.set_gid("dynamic")

            # Solar panel lines
            if sat.online:
                panel_len = 0.22
                angle_perp = sat.angle + math.pi / 2
                px = math.cos(angle_perp) * panel_len
                py = math.sin(angle_perp) * panel_len
                (panel_line,) = ax.plot(
                    [x - px, x + px], [y - py, y + py],
                    color=color, linewidth=1.8,
                    alpha=0.5, zorder=7
                )
                panel_line.set_gid("dynamic")

        sat_scatter = ax.scatter(
            xs,
            ys,
            c=colors,
            s=sizes,
            zorder=9,
            edgecolors="#ffffff",
            linewidths=0.4,
        )
        sat_scatter.set_gid("dynamic")

    # ── Draw Alerts ──────────────────────────────────────────

    def _draw_alerts(self, frame_num):
        active = [a for a in self.alerts if frame_num <= a["expiry"]]
        self.alerts = active
        for i, alert in enumerate(active[:3]):
            alpha = min(1.0, (alert["expiry"] - frame_num) / 30)
            alert_text = self.ax_orbit.text(
                0, -4.2 - i * 0.55,
                alert["msg"],
                ha="center", va="center",
                color=alert["color"],
                fontsize=10, fontfamily="monospace",
                fontweight="bold", alpha=alpha, zorder=20,
            )
            alert_text.set_gid("dynamic")

    # ── Draw Header ──────────────────────────────────────────

    def _draw_header(self, frame_num):
        online  = sum(1 for s in self.satellites if s.online and not s.is_faulty)
        faulty  = sum(1 for s in self.satellites if s.is_faulty and s.online)
        offline = sum(1 for s in self.satellites if not s.online)
        leader  = self._get_active_leader()
        leader_str = leader.node_id if leader else "NONE"
        frames_to_next = (ELECTION_EVERY - (frame_num % ELECTION_EVERY)) % ELECTION_EVERY
        secs_to_next = frames_to_next / FPS

        title_text = self.ax_orbit.text(
            0, 4.65,
            "SATELLITE CONSENSUS NETWORK",
            ha="center", va="center",
            color="#e8f4ff", fontsize=13,
            fontfamily="monospace", fontweight="bold", zorder=20,
        )
        title_text.set_gid("dynamic")

        status_text = self.ax_orbit.text(
            0, 4.25,
            f"FRAME {frame_num:05d}   |   TERM {self.raft.term}"
            f"   |   LEADER: {leader_str}"
            f"   |   HEALTHY: {online}   FAULTY: {faulty}"
            f"   OFFLINE: {offline}",
            ha="center", va="center",
            color="#4da6ff", fontsize=7.5,
            fontfamily="monospace", zorder=20, alpha=0.9,
        )
        status_text.set_gid("dynamic")

        countdown_text = self.ax_orbit.text(
            0,
            3.95,
            f"NEXT TERM IN: {secs_to_next:0.2f}s",
            ha="center",
            va="center",
            color="#9bc7ff",
            fontsize=7,
            fontfamily="monospace",
            zorder=20,
            alpha=0.9,
        )
        countdown_text.set_gid("dynamic")

        controls_text = self.ax_orbit.text(
            -4.85,
            4.65,
            "Keys: [+] add sat   [-] remove sat",
            ha="left",
            va="center",
            color="#6f95c4",
            fontsize=6.5,
            fontfamily="monospace",
            zorder=20,
            alpha=0.9,
        )
        controls_text.set_gid("dynamic")

        # Legend
        legend_items = [
            mpatches.Patch(color=ROLE_COLORS["leader"],    label="Leader"),
            mpatches.Patch(color=ROLE_COLORS["follower"],  label="Follower"),
            mpatches.Patch(color=ROLE_COLORS["faulty"],    label="Faulty"),
            mpatches.Patch(color=ROLE_COLORS["offline"],   label="Offline"),
        ]
        if self.legend_artist is not None:
            self.legend_artist.remove()

        self.legend_artist = self.ax_orbit.legend(
            handles=legend_items,
            loc="lower left", fontsize=7,
            facecolor="#080d1a", edgecolor="#1a2a44",
            labelcolor="white", framealpha=0.8,
        )

    # ── Draw Data Panel ──────────────────────────────────────

    def _draw_data_panel(self):
        ax = self.ax_data
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        ax.text(0.5, 0.97, "NODE TELEMETRY",
                ha="center", va="top",
                color="#4da6ff", fontsize=9,
                fontfamily="monospace", fontweight="bold", alpha=0.8)

        headers = ["NODE", "STATUS", "TEMP °C", "SIG dBm", "ALT km"]
        col_x   = [0.03, 0.22, 0.42, 0.62, 0.82]
        row_h   = 0.072
        start_y = 0.89

        # Header row
        for hdr, cx in zip(headers, col_x):
            ax.text(cx, start_y, hdr,
                    color="#4da6ff", fontsize=7,
                    fontfamily="monospace", fontweight="bold",
                    va="top")

        ax.axhline(start_y - 0.02, color="#1a2a44",
                   linewidth=0.8, xmin=0.02, xmax=0.98)

        for i, sat in enumerate(self.satellites):
            y = start_y - 0.04 - i * row_h

            role = sat.role if sat.online else "offline"
            if sat.is_faulty and sat.online:
                role = "faulty"
            color = ROLE_COLORS.get(role, "#888")

            if not sat.online:
                status = "OFFLINE"
                t_str  = "---"
                s_str  = "---"
                a_str  = "---"
            elif sat.is_faulty:
                status = "FAULTY"
                t_str  = f"{sat.temperature:.1f}"
                s_str  = f"{sat.signal_strength:.1f}"
                a_str  = f"{sat.altitude:.0f}"
            else:
                status = sat.role.upper()
                t_str  = f"{sat.temperature:.1f}"
                s_str  = f"{sat.signal_strength:.1f}"
                a_str  = f"{sat.altitude:.0f}"

            row_data = [sat.node_id, status, t_str, s_str, a_str]
            for val, cx in zip(row_data, col_x):
                ax.text(cx, y, val,
                        color=color, fontsize=7,
                        fontfamily="monospace", va="top")

    # ── Draw Event Log ───────────────────────────────────────

    def _draw_event_log(self):
        ax = self.ax_log
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        ax.text(0.5, 0.97, "EVENT LOG",
                ha="center", va="top",
                color="#4da6ff", fontsize=9,
                fontfamily="monospace", fontweight="bold", alpha=0.8)

        ax.axhline(0.90, color="#1a2a44",
                   linewidth=0.8, xmin=0.02, xmax=0.98)

        for i, event in enumerate(self.event_log[:12]):
            y      = 0.88 - i * 0.074
            alpha  = max(0.3, 1.0 - i * 0.06)
            color  = event["color"] if i == 0 else "#3a5070"
            ax.text(0.04, y,
                    f"{event['ts']}  {event['msg']}",
                    color=color, fontsize=7,
                    fontfamily="monospace", va="top", alpha=alpha)

    # ── Run ──────────────────────────────────────────────────

    def run(self):
        print("Starting visualizer — close the window to stop.")
        print("Tip: maximise the window before recording!\n")
        print(f"Event log file: {self.log_file_path}\n")

        # Draw the first frame immediately so data is visible at startup.
        self.update(0)

        self.ani = animation.FuncAnimation(
            self.fig,
            self.update,
            frames=None,          # run forever
            interval=1000 / FPS,
            blit=False,
            cache_frame_data=False,
        )

        plt.tight_layout(pad=0)
        plt.show()


# ── Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    viz = SatelliteVisualizer()
    viz.run()