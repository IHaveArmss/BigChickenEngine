"""CutsceneManager — waypoint-based cutscene system with recording, playback, and Dev UI integration."""

import os
import json
import glm


class CutsceneManager:
    def __init__(self, engine):
        self.engine = engine
        self.waypoints = []
        self.playback_index = 0
        self.playback_progress = 0.0
        self.playback_speed = 1.0
        self.can_player_move = True
        self.is_playing = False
        self.is_looping = False
        self._saved_camera_pos = None
        self._saved_camera_yaw = None
        self._saved_camera_pitch = None
        self._play_camera = None

    def add_waypoint(self):
        """Capture current camera state and add as a waypoint."""
        cam = self.engine.active_camera
        waypoint = {
            "pos": [cam.position.x, cam.position.y, cam.position.z],
            "yaw": cam.yaw,
            "pitch": cam.pitch,
        }
        self.waypoints.append(waypoint)

    def clear(self):
        """Reset waypoint list."""
        self.waypoints = []
        self.playback_index = 0
        self.playback_progress = 0.0
        self.is_playing = False

    def play(self):
        """Start playback from the beginning."""
        if len(self.waypoints) < 2:
            print("[Cutscene] Need at least 2 waypoints to play")
            return
        if self.is_playing:
            return
        cam = self.engine.active_camera
        self._saved_camera_pos = glm.vec3(cam.position)
        self._saved_camera_yaw = cam.yaw
        self._saved_camera_pitch = cam.pitch
        self._play_camera = _CutsceneCamera()
        self.playback_index = 0
        self.playback_progress = 0.0
        self.is_playing = True
        self.engine.set_play_camera(self._play_camera)

    def stop(self):
        """Stop playback."""
        if not self.is_playing:
            return
        self.is_playing = False
        self.engine.set_play_camera(None)
        self._play_camera = None
        if self._saved_camera_pos is not None:
            cam = self.engine.active_camera
            cam.position = self._saved_camera_pos
            cam.yaw = self._saved_camera_yaw
            cam.pitch = self._saved_camera_pitch
            cam._update_vectors()

    def update(self, dt):
        """Per-frame update for playback."""
        if not self.is_playing or len(self.waypoints) < 2:
            return
        num_segments = len(self.waypoints) - 1
        current_idx = min(self.playback_index, num_segments - 1)
        next_idx = current_idx + 1
        wp1 = self.waypoints[current_idx]
        wp2 = self.waypoints[next_idx]
        p1 = glm.vec3(wp1["pos"])
        p2 = glm.vec3(wp2["pos"])
        dist = glm.length(p2 - p1)
        if dist < 0.001:
            local_t = 1.0
        else:
            segment_time = dist / (self.playback_speed * 5.0)
            if segment_time > 0:
                local_t = min(1.0, dt / segment_time)
            else:
                local_t = 1.0
        self.playback_progress += local_t
        if self.playback_progress >= 1.0:
            self.playback_progress = 0.0
            self.playback_index += 1
            if self.playback_index >= num_segments:
                if self.is_looping:
                    self.playback_index = 0
                else:
                    self.is_playing = False
                    self.engine.set_play_camera(None)
                    self._play_camera = None
                    return
        t = self._smoothstep(self.playback_progress)
        self._play_camera.position = glm.vec3(
            glm.mix(p1.x, p2.x, t),
            glm.mix(p1.y, p2.y, t),
            glm.mix(p1.z, p2.z, t),
        )
        self._play_camera.yaw = self._lerp_angle(wp1["yaw"], wp2["yaw"], t)
        self._play_camera.pitch = self._lerp_angle(wp1["pitch"], wp2["pitch"], t)
        self._play_camera._update_vectors()

    @staticmethod
    def _lerp_angle(a, b, t):
        """Linearly interpolate between two angles using the shortest path."""
        diff = (b - a + 180) % 360 - 180
        return a + diff * t

    def save(self, name):
        """Save waypoints to assets/cutscenes/{name}.json."""
        os.makedirs("assets/cutscenes", exist_ok=True)
        filepath = os.path.join("assets/cutscenes", f"{name}.json").replace("\\", "/")
        data = {
            "waypoints": self.waypoints,
            "can_player_move": self.can_player_move,
            "is_looping": self.is_looping,
            "playback_speed": self.playback_speed,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[Cutscene] Saved: {filepath}")

    def load(self, name):
        """Load waypoints from assets/cutscenes/{name}.json."""
        filepath = os.path.join("assets/cutscenes", f"{name}.json").replace("\\", "/")
        if not os.path.exists(filepath):
            print(f"[Cutscene] File not found: {filepath}")
            return False
        with open(filepath, "r") as f:
            data = json.load(f)
        self.waypoints = data.get("waypoints", [])
        self.can_player_move = data.get("can_player_move", True)
        self.is_looping = data.get("is_looping", False)
        self.playback_speed = data.get("playback_speed", 1.0)
        self.playback_index = 0
        self.playback_progress = 0.0
        self.is_playing = False
        print(f"[Cutscene] Loaded: {filepath}")
        return True

    def list_cutscenes(self):
        """Return list of available cutscene names."""
        os.makedirs("assets/cutscenes", exist_ok=True)
        files = []
        for f in os.listdir("assets/cutscenes"):
            if f.endswith(".json"):
                files.append(f[:-5])
        return sorted(files)

    def get_camera_state(self):
        """Returns interpolated (pos, yaw, pitch) for the current playback state."""
        if len(self.waypoints) < 2:
            return None
        num_segments = len(self.waypoints) - 1
        current_idx = min(self.playback_index, num_segments - 1)
        next_idx = current_idx + 1
        wp1 = self.waypoints[current_idx]
        wp2 = self.waypoints[next_idx]
        p1 = glm.vec3(wp1["pos"])
        p2 = glm.vec3(wp2["pos"])
        t = self._smoothstep(self.playback_progress)
        pos = glm.vec3(
            glm.mix(p1.x, p2.x, t),
            glm.mix(p1.y, p2.y, t),
            glm.mix(p1.z, p2.z, t),
        )
        yaw = glm.mix(wp1["yaw"], wp2["yaw"], t)
        pitch = glm.mix(wp1["pitch"], wp2["pitch"], t)
        return pos, yaw, pitch

    @staticmethod
    def _smoothstep(t):
        return t * t * (3.0 - 2.0 * t)


from core.camera import Camera

class _CutsceneCamera(Camera):
    """Internal camera used during cutscene playback."""
    def __init__(self):
        super().__init__(position=glm.vec3(0, 5, 15), yaw=-90.0, pitch=0.0)
