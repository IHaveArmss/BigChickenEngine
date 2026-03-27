import pygame
import pybullet as p
from pyglm import glm

class PlayerController:
    def start(self):
        print(f"[PlayerController] Attached to {self.entity.name}")
        self.body_id = getattr(self.entity, 'pybullet_body_id', None)
        self.phys = self.engine.physics_system
        self.speed = 8.0
        self.jump_force = 6.0
        # Time-based grounding (set in on_collision, decays in fixed_update)
        self.ground_time = 0.0

    def on_collision(self, collision):
        # Normal pointing "up" at the player
        if collision.normal.y > 0.5:
            self.ground_time = 0.1 # Stay grounded for 100ms after a hit

    def fixed_update(self, fixed_dt):
        self.body_id = getattr(self.entity, 'pybullet_body_id', None)
        if self.body_id is None: return
        
        # Decay grounding timer
        if self.ground_time > 0:
            self.ground_time -= fixed_dt

        keys = pygame.key.get_pressed()
        
        # 1. Dynamic Movement
        if not getattr(self.entity, 'is_kinematic', True) and getattr(self.entity, 'mass', 1.0) > 0:
            linear_v, _ = p.getBaseVelocity(self.body_id, physicsClientId=self.phys.client_id)
            vx, vy, vz = 0.0, linear_v[1], 0.0
            
            if keys[pygame.K_w]: vz -= self.speed
            if keys[pygame.K_s]: vz += self.speed
            if keys[pygame.K_a]: vx -= self.speed
            if keys[pygame.K_d]: vx += self.speed
            
            # Jump if grounded
            if keys[pygame.K_SPACE] and self.ground_time > 0:
                vy = self.jump_force
                self.ground_time = 0.0 # Force off ground
            
            p.resetBaseVelocity(self.body_id, [vx, vy, vz], [0, 0, 0], physicsClientId=self.phys.client_id)
        
        # 2. Kinematic Movement
        else:
            pos = self.entity.position
            move = self.speed * fixed_dt
            if keys[pygame.K_w]: pos.z -= move
            if keys[pygame.K_s]: pos.z += move
            if keys[pygame.K_a]: pos.x -= move
            if keys[pygame.K_d]: pos.x += move
            if keys[pygame.K_SPACE]: pos.y += move # fly
            
            self.entity.position = pos

    def update(self, dt):
        pass
