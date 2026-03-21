"""Test script for runtime spawn/destroy and tags.

Attach to any object. During Play Mode:
  - Press F to spawn a red cube that falls with gravity
  - Press G to spawn a prefab (if 'test_ball' prefab exists)
  - Spawned cubes auto-destroy after 5 seconds
  - Press X to destroy ALL objects tagged 'spawned'
"""

import pygame
from pyglm import glm


class SpawnDestroyTest:
    def start(self):
        self.spawn_cooldown = 0.0
        self.spawned_timers = []
        print("[SpawnDestroyTest] F=spawn cube, X=destroy all 'spawned', G=spawn prefab")

    def update(self, dt):
        self.spawn_cooldown -= dt
        keys = pygame.key.get_pressed()

        if keys[pygame.K_f] and self.spawn_cooldown <= 0:
            self.spawn_cooldown = 0.3

            cam = self.engine.active_camera
            spawn_pos = cam.position + cam.front * 3.0
            pos = [spawn_pos.x, spawn_pos.y, spawn_pos.z]

            obj = self.engine.spawn(
                "cube",
                name="spawned_cube",
                position=pos,
                scale=[0.5, 0.5, 0.5],
                color=[1.0, 0.2, 0.2],
                tag="spawned",
                is_kinematic=False,
                use_gravity=True,
                mass=1.0,
                bounciness=0.5,
            )
            if obj:
                self.spawned_timers.append((obj, 5.0))
                print(f"[SpawnDestroyTest] Spawned cube at {pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}")

        if keys[pygame.K_g] and self.spawn_cooldown <= 0:
            self.spawn_cooldown = 0.3
            cam = self.engine.active_camera
            spawn_pos = cam.position + cam.front * 3.0
            obj = self.engine.spawn_prefab(
                "test_ball",
                position=[spawn_pos.x, spawn_pos.y, spawn_pos.z],
                tag="spawned",
            )
            if obj:
                print(f"[SpawnDestroyTest] Spawned prefab 'test_ball'")

        if keys[pygame.K_x]:
            targets = self.engine.find_by_tag("spawned")
            for t in targets:
                self.engine.destroy(t)
            if targets:
                print(f"[SpawnDestroyTest] Destroyed {len(targets)} objects tagged 'spawned'")
            self.spawned_timers.clear()

        remaining = []
        for obj, timer in self.spawned_timers:
            timer -= dt
            if timer <= 0:
                self.engine.destroy(obj)
            else:
                remaining.append((obj, timer))
        self.spawned_timers = remaining

    def stop(self):
        print("[SpawnDestroyTest] Stopped.")
