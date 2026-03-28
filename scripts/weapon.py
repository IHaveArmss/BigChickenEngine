import pygame
import glm
from core.physics_system import PhysicsSystem

class Weapon:
    def start(self):
        self.weapon_drawn = False
        self.last_f_pressed = False
        self.markers = [] # list of (obj, time_remaining)
        print(f"[Weapon] Initialized on {self.entity.name}. Press 'F' to draw/holster.")

    def update(self, dt):
        # Skip logic if in Dev Mode
        if self.engine.dev_mode:
            return

        # Handle Toggle (F key)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_f] and not self.last_f_pressed:
            self.weapon_drawn = not self.weapon_drawn
            status = "DRAWN" if self.weapon_drawn else "HOLSTERED"
            print(f"[Weapon] {status}")
        self.last_f_pressed = keys[pygame.K_f]

        # Cleanup markers
        expired = []
        for i, (marker_obj, timer) in enumerate(self.markers):
            timer -= dt
            if timer <= 0:
                self.engine.destroy(marker_obj)
                expired.append(i)
            else:
                self.markers[i] = (marker_obj, timer)
        
        for i in reversed(expired):
            self.markers.pop(i)

    def on_mouse_down(self, button):
        if not self.weapon_drawn or self.engine.dev_mode or button != 1:
            return

        # Fire Raycast
        cam = self.engine.active_camera
        ray_from = cam.position
        ray_to = cam.position + cam.front * 200.0

        print("[Weapon] FIRE!")
        
        # Detailed raycast to get position and object
        hit_data = self.engine.physics_system.raycast_detailed(ray_from, ray_to, ignore=[self.entity])
        
        if hit_data:
            hit_obj, hit_pos, _, _ = hit_data
            
            # 1. Spawn a marker cube at hit point
            # No physics, small scale, red color
            marker = self.engine.spawn(
                'cube', 
                name='bullet_marker',
                position=list(hit_pos),
                scale=[0.15, 0.15, 0.15],
                color=[1, 0, 0],
                is_collideable=False
            )
            self.markers.append((marker, 1.0)) # 1 second lifetime

            # 2. Check for NPC hit
            if getattr(hit_obj, 'tag', '') == 'npc':
                print(f"[Weapon] ELIMINATED: {hit_obj.name}")
                self.engine.destroy(hit_obj)
        else:
            print("[Weapon] Miss...")
