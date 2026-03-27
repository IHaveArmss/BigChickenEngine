from core.camera import Camera
import pygame
from pyglm import glm

class CameraFollow:
    def start(self):
        print(f"[CameraFollow] Attached to {self.entity.name}")
        
        # Create a new Camera instance that will act as the player's view
        self.camera = Camera(position=self.entity.position)
        self.engine.set_play_camera(self.camera)
        
        # Settings for follow script
        self.distance = 8.0     # Distance from player
        self.y_offset = 1.5     # How high above the player center to aim
        self.yaw = 90.0         # Orbit horizontal angle
        self.pitch = 20.0       # Orbit vertical angle
        self.sensitivity = 0.2  # Mouse sensitivity
        
        # Lock mouse to screen for clean free-look
        pygame.mouse.get_rel()
        
    def update(self, dt):
        # 1. Process Mouse Input to orbit camera
        rel_x, rel_y = pygame.mouse.get_rel()
        
        self.yaw += rel_x * self.sensitivity
        self.pitch -= rel_y * self.sensitivity
        
        # Clamp pitch so we don't flip upside down
        self.pitch = max(-89.0, min(89.0, self.pitch))
        
        # 2. Calculate Orbital Position (Spherical Coordinates)
        rad_yaw = glm.radians(self.yaw)
        rad_pitch = glm.radians(self.pitch)
        
        # Trig to convert spherical angles to 3D Cartesian offset
        offset_x = self.distance * glm.cos(rad_pitch) * glm.cos(rad_yaw)
        offset_y = self.distance * glm.sin(rad_pitch)
        offset_z = self.distance * glm.cos(rad_pitch) * glm.sin(rad_yaw)
        
        # Target is player pos + a slight upward offset so we don't look at their feet
        target_pos = self.entity.position + glm.vec3(0.0, self.y_offset, 0.0)
        
        # Place camera
        self.camera.position = target_pos + glm.vec3(offset_x, offset_y, offset_z)
        
        # 3. Always strictly face the target
        self.camera.front = glm.normalize(target_pos - self.camera.position)
        self.camera.right = glm.normalize(glm.cross(self.camera.front, glm.vec3(0.0, 1.0, 0.0)))
        self.camera.up = glm.normalize(glm.cross(self.camera.right, self.camera.front))
