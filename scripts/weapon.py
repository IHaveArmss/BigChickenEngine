import pygame
import glm
from core.physics_system import PhysicsSystem

class Weapon:
    def start(self):
        self.weapon_drawn = False
        self.last_f_pressed = False
        self.markers = [] # list of (obj, time_remaining)
        self.tp_timer = 0.0 # Timer for narrative teleport
        self.fire_cooldown = 0.0 # Timer for firing delay
        print(f"[Weapon] Initialized on {self.entity.name}. Press 'F' to draw/holster.")

    def update(self, dt):
        # 1. Update Cooldown Timer (Always)
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt

        # Skip rest if in Dev Mode
        if self.engine.dev_mode:
            return

        # Handle Toggle (F key)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_f] and not self.last_f_pressed:
            self.weapon_drawn = not self.weapon_drawn
            status = "DRAWN" if self.weapon_drawn else "HOLSTERED"
            print(f"[Weapon] {status}")

            # Swap our animation set if we have a state controller
            controller = getattr(self.entity, 'anim_state_controller', None)
            if controller:
                if self.weapon_drawn:
                    controller.idle_clip = "pistol_Idle"
                    controller.run_clip = "pistol_run"
                    controller.jump_clip = "pistol_jump"
                else:
                    controller.idle_clip = "Idle"
                    controller.run_clip = "Running"
                    controller.jump_clip = "Jump"
                
                controller.refresh()
                clip_name = controller._resolved.get(controller._current_state)
                if clip_name:
                    controller.animator.crossfade(clip_name, duration=0.15)
        self.last_f_pressed = keys[pygame.K_f]

        # Handle Narrative Teleport Timer
        if self.tp_timer > 0:
            self.tp_timer -= dt
            if self.tp_timer <= 0:
                print("[Weapon] Narrative teleport triggered!")
                self.engine.load_scene('scenes/pizza.json')

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

        # 2. Check Cooldown
        if self.fire_cooldown > 0:
            return
            
        # Reset Cooldown (0.5s)
        self.fire_cooldown = 0.5
        
        # 3. Play Gunshot SFX
        self.engine.audio.play_sfx('assets/sounds/gunshot.mp3')

        # Fire Raycast
        cam = self.engine.active_camera
        # Start from player head height to prevent self-hitting or weird angles
        ray_from = self.entity.position + glm.vec3(0, 1.5, 0)
        ray_to = ray_from + cam.front * 200.0

        print("[Weapon] FIRE!")
        
        hit_data = self.engine.physics_system.raycast_detailed(ray_from, ray_to, ignore=[self.entity])
        
        if hit_data:
            hit_obj, hit_pos, _, _ = hit_data
            
            # Spawn bullet marker
            marker = self.engine.spawn(
                'cube', 
                name='bullet_marker',
                position=list(hit_pos),
                scale=[0.15, 0.15, 0.15],
                color=[1, 0, 0],
                is_collideable=False
            )
            self.markers.append((marker, 1.0))

            # Check for NPC hit
            if getattr(hit_obj, 'tag', '') == 'npc':
                if hit_obj.alpha > 0.5:
                    print(f"[Weapon] HIT NPC: {hit_obj.name}")
                    hit_obj.alpha = 0.5
                    
                    self.engine.audio.play_sfx('assets/sounds/bloodGushing.mp3')
                    self.engine.show_image_overlay('assets/transitions/act2.jpg', 3.0)
                    self.engine.global_flags['thief_shot'] = True
                    self.tp_timer = 3.0
                else:
                    print(f"[Weapon] ALREADY DEAD: {hit_obj.name}")
        else:
            print("[Weapon] Miss...")
