from core.camera import Camera
from pyglm import glm


class CutsceneCamera:
    def start(self):
        self.camera = Camera(position=glm.vec3(0.0, 5.0, 20.0))

        self.waypoints = [
            (0.0, 5.0, 20.0,  -90.0, 0.0),   # Start: wide shot
            (5.0, 3.0, 10.0,  -90.0, 10.0),  # Move closer
            (0.0, 2.0, 5.0,   -90.0, 15.0),  # Low angle
            (0.0, 10.0, 2.0,  -90.0, 30.0),  # Top-down view
            (0.0, 5.0, 20.0,  -90.0, 40.0),  # Return to start
        ]

        self.duration = 40.0
        self.elapsed = 0.0
        self.active = False
        self.finished = False

    def trigger(self):
        self.active = True
        self.elapsed = 0.0
        self.engine.set_play_camera(self.camera)

    def on_interact(self):
        self.trigger()

    def update(self, dt):
        if not self.active or self.finished:
            return

        self.elapsed += dt
        progress = min(self.elapsed / self.duration, 1.0)

        num_waypoints = len(self.waypoints)
        segment = int(progress * (num_waypoints - 1))
        segment = min(segment, num_waypoints - 2)

        local_t = (progress * (num_waypoints - 1)) - segment

        wp1 = self.waypoints[segment]
        wp2 = self.waypoints[segment + 1]

        self.camera.position = glm.vec3(
            glm.mix(wp1[0], wp2[0], local_t),
            glm.mix(wp1[1], wp2[1], local_t),
            glm.mix(wp1[2], wp2[2], local_t),
        )

        self.camera.yaw = glm.mix(wp1[3], wp2[3], local_t)
        self.camera.pitch = glm.mix(wp1[4], wp2[4], local_t)
        self.camera._update_vectors()

        if progress >= 1.0:
            self.active = False
            self.finished = True
            print("[Cutscene] Done!")
