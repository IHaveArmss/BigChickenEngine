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
        self.cam_distance   = 5.0        # orbit radius
        self.current_distance = 5.0      # actual distance (may be reduced by collision)
        self.cam_height     = 2.0        # look-at height above player pivot
        self.cam_smoothness = 8.0        # position lerp speed (higher = snappier)
        self.sensitivity    = 0.2        # mouse degrees-per-pixel
        self.cam_collision_smoothness = 10.0  # speed for camera distance smoothing

        # Camera angles (degrees)
        # Initialize from the entity's actual spawn rotation so scene transitions work
        start_rot = getattr(self.entity, 'rotation_euler', None)
        if start_rot:
            self.cam_yaw = start_rot.y - 180.0
        else:
            self.cam_yaw = 0.0
            
        self.cam_pitch = 15.0            # slight downward look

        # Register this entity as the player for interaction detection
        self.engine.interaction_manager.set_player(self.entity)

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

        if not self.engine.input_enabled:
            p.resetBaseVelocity(body_id, [0.0, 0.0, 0.0], [0, 0, 0],
                                physicsClientId=self.phys.client_id)
            return

        # Freeze movement during dialogue (zero horizontal velocity, keep gravity)
        if self.engine.dialogue.active:
            is_dynamic = (not getattr(self.entity, 'is_kinematic', True)
                          and getattr(self.entity, 'mass', 1.0) > 0)
            if is_dynamic:
                lin_v, _ = p.getBaseVelocity(body_id, physicsClientId=self.phys.client_id)
                p.resetBaseVelocity(body_id, [0, lin_v[1], 0], [0, 0, 0],
                                    physicsClientId=self.phys.client_id)
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
            elif vy > 0 and self.ground_time > 0:
                # Edge/corner contacts can inject upward velocity into the body.
                # Discard it when grounded so the player doesn't "jump" on curbs.
                vy = 0.0

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

    def update(self, dt):
        # -------- mouse input → orbit angles --------
        rel_x, rel_y = pygame.mouse.get_rel()
        if not self.engine.input_enabled:
            return
        self.cam_yaw   -= rel_x * self.sensitivity
        self.cam_pitch += rel_y * self.sensitivity
        self.cam_pitch  = max(-60.0, min(75.0, self.cam_pitch))

        # -------- player always faces away from camera --------
        # Move this ABOVE the dialogue check so the player pivots to face
        # the look-direction even during conversations.
        self.entity.set_rotation_euler(0.0, self.cam_yaw + 180.0, 0.0)

        # DialogueManager controls the camera during dialogue
        if self.engine.dialogue.active:
            return

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

        # -------- camera collision detection --------
        target_distance = self.cam_distance
        CAM_MARGIN = 0.25   # keep camera this far in front of any surface

        hit_data = self.phys.raycast_detailed(
            focus, ideal, ignore={self.entity})

        if hit_data:
            _, hit_pos, hit_fraction, _ = hit_data
            if hit_fraction < 1.0:
                hit_dist = self.cam_distance * hit_fraction
                target_distance = max(hit_dist - CAM_MARGIN, 0.1)

        # Snap instantly when moving closer — lerping through geometry causes
        # the visible clip-through. Only smooth the retreat (camera pulling back).
        if target_distance < self.current_distance:
            self.current_distance = target_distance
        else:
            t_dist = min(1.0, dt * self.cam_collision_smoothness)
            self.current_distance = glm.mix(self.current_distance, target_distance, t_dist)
        
        current_offset = glm.vec3(
            self.current_distance * glm.cos(rad_pitch) *  glm.sin(rad_yaw),
            self.current_distance * glm.sin(rad_pitch),
            self.current_distance * glm.cos(rad_pitch) *  glm.cos(rad_yaw),
        )
        ideal = focus + current_offset

        # -------- smooth follow (lerp) --------
        t = min(1.0, dt * self.cam_smoothness)
        self.camera.position = glm.mix(self.camera.position, ideal, t)

        # -------- always look at the focus point --------
        to_focus = glm.normalize(focus - self.camera.position)
        self.camera.front = to_focus
        self.camera.right = glm.normalize(glm.cross(to_focus, glm.vec3(0, 1, 0)))
        self.camera.up    = glm.normalize(glm.cross(self.camera.right, to_focus))
