"""
Third-Person Controller
=======================
Attach ONLY this script to your player object. It handles:
  - Mouse orbit camera (smooth follow behind the player)
  - Camera-relative WASD movement
  - Player auto-rotates to face camera direction
  - Jump with Space

Do NOT also attach player_controller or camera_follow — this replaces both.
"""

import pygame
import pybullet as p
from pyglm import glm
from core.camera import Camera


class ThirdPerson:
    # ------------------------------------------------------------------ #
    # Lifecycle                                                           #
    # ------------------------------------------------------------------ #
    def start(self):
        print(f"[ThirdPerson] Attached to {self.entity.name}")

        # Physics refs
        self.phys = self.engine.physics_system

        # Movement tuning
        self.move_speed   = 8.0
        self.jump_force   = 6.0
        self.ground_time  = 0.0          # > 0 while on ground

        # Camera tuning
        self.cam_distance   = 6.0        # orbit radius
        self.cam_height     = 2.0        # look-at height above player pivot
        self.cam_smoothness = 8.0        # position lerp speed (higher = snappier)
        self.sensitivity    = 0.2        # mouse degrees-per-pixel

        # Camera angles (degrees)
        self.cam_yaw   = 0.0             # 0 = behind the player (-Z in world)
        self.cam_pitch = 15.0            # slight downward look

        # Create the play-mode camera and register it
        self.camera = Camera(position=self.entity.position + glm.vec3(0, self.cam_height, self.cam_distance))
        self.engine.set_play_camera(self.camera)

        # Eat any stale mouse delta
        pygame.mouse.get_rel()

    # ------------------------------------------------------------------ #
    # Collision (grounding)                                               #
    # ------------------------------------------------------------------ #
    def on_collision(self, collision):
        if collision.normal.y > 0.5:
            self.ground_time = 0.15       # 150 ms forgiveness window

    # ------------------------------------------------------------------ #
    # fixed_update — runs once per physics substep                       #
    # ------------------------------------------------------------------ #
    def fixed_update(self, fixed_dt):
        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is None:
            return

        # Decay grounding timer
        if self.ground_time > 0:
            self.ground_time -= fixed_dt

        keys = pygame.key.get_pressed()

        # -------- directions from camera yaw --------
        rad = glm.radians(self.cam_yaw)
        # "forward" = where the camera is looking (flattened to XZ)
        forward = glm.vec3(-glm.sin(rad), 0.0, -glm.cos(rad))
        right   = glm.vec3( glm.cos(rad), 0.0, -glm.sin(rad))

        move = glm.vec3(0.0)
        if keys[pygame.K_w]: move += forward
        if keys[pygame.K_s]: move -= forward
        if keys[pygame.K_a]: move -= right
        if keys[pygame.K_d]: move += right

        if glm.length(move) > 0.001:
            move = glm.normalize(move)

        # -------- rotate the player mesh to face movement direction --------
        if glm.length(move) > 0.001:
            face_angle = glm.degrees(glm.atan2(move.x, move.z))
            self.entity.set_rotation_euler(0.0, face_angle, 0.0)

        # -------- apply velocity (dynamic body) --------
        is_dynamic = (not getattr(self.entity, 'is_kinematic', True)
                      and getattr(self.entity, 'mass', 1.0) > 0)

        if is_dynamic:
            lin_v, _ = p.getBaseVelocity(body_id, physicsClientId=self.phys.client_id)
            vy = lin_v[1]                               # keep gravity

            vx = move.x * self.move_speed
            vz = move.z * self.move_speed

            if keys[pygame.K_SPACE] and self.ground_time > 0:
                vy = self.jump_force
                self.ground_time = 0.0

            p.resetBaseVelocity(body_id,
                                [vx, vy, vz], [0, 0, 0],
                                physicsClientId=self.phys.client_id)
        else:
            # Kinematic fallback
            step = self.move_speed * fixed_dt
            pos  = self.entity.position
            pos += move * step
            if keys[pygame.K_SPACE]:
                pos.y += step
            self.entity.position = pos

    # ------------------------------------------------------------------ #
    # update — runs once per frame (camera)                              #
    # ------------------------------------------------------------------ #
    def update(self, dt):
        # -------- mouse input → orbit angles --------
        rel_x, rel_y = pygame.mouse.get_rel()
        self.cam_yaw   += rel_x * self.sensitivity
        self.cam_pitch -= rel_y * self.sensitivity
        self.cam_pitch  = max(-60.0, min(75.0, self.cam_pitch))

        # -------- player always faces camera direction --------
        self.entity.set_rotation_euler(0.0, -self.cam_yaw, 0.0)

        # -------- ideal camera position (spherical offset) --------
        rad_yaw   = glm.radians(self.cam_yaw)
        rad_pitch = glm.radians(self.cam_pitch)

        offset = glm.vec3(
            self.cam_distance * glm.cos(rad_pitch) *  glm.sin(rad_yaw),
            self.cam_distance * glm.sin(rad_pitch),
            self.cam_distance * glm.cos(rad_pitch) *  glm.cos(rad_yaw),
        )

        focus  = self.entity.position + glm.vec3(0.0, self.cam_height, 0.0)
        ideal  = focus + offset

        # -------- smooth follow (lerp) --------
        t = min(1.0, dt * self.cam_smoothness)
        self.camera.position = glm.mix(self.camera.position, ideal, t)

        # -------- always look at the focus point --------
        to_focus = glm.normalize(focus - self.camera.position)
        self.camera.front = to_focus
        self.camera.right = glm.normalize(glm.cross(to_focus, glm.vec3(0, 1, 0)))
        self.camera.up    = glm.normalize(glm.cross(self.camera.right, to_focus))
