import pygame
import math
import pybullet as p
import glm
from core.physics_system import PhysicsSystem

# Clip names for each locomotion state, per mode
_BASE_CLIPS = {
    'idle': 'Idle',
    'run':  'Running',
    'jump': 'Jump',
    'fall': 'Falling',
}
_GUN_CLIPS = {
    'idle': 'pistol_Idle',
    'run':  'pistol_run',
    'jump': 'pistol_jump',
    'fall': 'Falling',   # no gun-fall anim – reuse base
}

MOVE_THRESHOLD    = 0.1   # horizontal speed to enter 'run'
VERTICAL_THRESHOLD = 0.15  # |vy| to enter 'jump' / 'fall'


class Weapon:
    # ------------------------------------------------------------------ #
    # Lifecycle                                                           #
    # ------------------------------------------------------------------ #
    def start(self):
        self.weapon_drawn   = False
        self.last_f_pressed = False
        self.markers        = []   # list of (obj, time_remaining)
        self.tp_timer       = 0.0  # timer for narrative teleport
        self.fire_cooldown  = 0.0  # timer for firing delay

        # Internal animation state when gun is out (prevents redundant crossfades)
        self._gun_loco_state = None

        print(f"[Weapon] Initialized on {self.entity.name}. Press 'F' to draw/holster.")

    # ------------------------------------------------------------------ #
    # Update                                                              #
    # ------------------------------------------------------------------ #
    def update(self, dt):
        # Always tick cooldown
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt

        if self.engine.dev_mode:
            return

        keys = pygame.key.get_pressed()

        # ---- F key: toggle equip ----
        if keys[pygame.K_f] and not self.last_f_pressed:
            self.weapon_drawn = not self.weapon_drawn
            self._on_weapon_toggled()

        self.last_f_pressed = keys[pygame.K_f]

        # ---- Drive gun animations manually every frame ----
        if self.weapon_drawn:
            self._update_gun_anims()

        # ---- Narrative teleport timer ----
        if self.tp_timer > 0:
            self.tp_timer -= dt
            if self.tp_timer <= 0:
                print("[Weapon] Narrative teleport triggered!")
                self.engine.load_scene('scenes/pizza.json')

        # ---- Cleanup bullet markers ----
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

    # ------------------------------------------------------------------ #
    # Toggle handler                                                      #
    # ------------------------------------------------------------------ #
    def _on_weapon_toggled(self):
        status = "DRAWN" if self.weapon_drawn else "HOLSTERED"
        print(f"[Weapon] {status}")

        animator   = getattr(self.entity, 'animator', None)
        controller = getattr(self.entity, 'anim_state_controller', None)

        if animator is None:
            return

        if self.weapon_drawn:
            # --- Equip ---
            # Hand animation control to this script; freeze the state controller
            # so it cannot override our choices.
            self.entity.use_anim_state_controller = False
            self._gun_loco_state = None  # force re-evaluate on next tick

            # Immediately start the gun-idle so the transition is instant
            self._crossfade_gun('idle', animator)

        else:
            # --- Holster ---
            # Restore the state controller.  Reset its internal state so it
            # forces a fresh crossfade on the very next tick (no stale state).
            if controller is not None:
                controller.idle_clip = 'Idle'
                controller.run_clip  = 'Running'
                controller.jump_clip = 'Jump'
                controller.fall_clip = 'Falling'
                controller.refresh()
                controller._current_state = None  # force re-evaluation
            self.entity.use_anim_state_controller = True

            # Crossfade to base idle right away so there's no blank frame
            animator.crossfade('Idle', duration=0.15, loop=True)

    # ------------------------------------------------------------------ #
    # Per-frame gun animation driver                                      #
    # ------------------------------------------------------------------ #
    def _update_gun_anims(self):
        """Sample physics velocity and crossfade to the correct gun clip."""
        animator = getattr(self.entity, 'animator', None)
        if animator is None:
            return

        vx, vy, vz = self._sample_velocity()
        h_speed = (vx * vx + vz * vz) ** 0.5

        if vy > VERTICAL_THRESHOLD:
            loco = 'jump'
        elif vy < -VERTICAL_THRESHOLD:
            loco = 'fall'
        elif h_speed > MOVE_THRESHOLD:
            loco = 'run'
        else:
            loco = 'idle'

        if loco != self._gun_loco_state:
            self._crossfade_gun(loco, animator)
            self._gun_loco_state = loco

    def _crossfade_gun(self, loco_state, animator):
        clip_name = _GUN_CLIPS.get(loco_state)
        if clip_name is None:
            return
        animator.crossfade(clip_name, duration=0.15, loop=True)
        print(f"[Weapon] Gun anim → '{clip_name}'")

    # ------------------------------------------------------------------ #
    # Velocity helper                                                     #
    # ------------------------------------------------------------------ #
    def _sample_velocity(self):
        """Return (vx, vy, vz) from the physics body, or (0,0,0)."""
        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is None:
            return 0.0, 0.0, 0.0
        is_kinematic = getattr(self.entity, 'is_kinematic', True)
        if is_kinematic:
            return 0.0, 0.0, 0.0
        phys = self.engine.physics_system
        lin_vel, _ = p.getBaseVelocity(body_id, physicsClientId=phys.client_id)
        return float(lin_vel[0]), float(lin_vel[1]), float(lin_vel[2])

    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    # Shooting (AoE Cone)                                               #
    # ------------------------------------------------------------------ #
    def on_mouse_down(self, button):
        if not self.weapon_drawn or self.engine.dev_mode or button != 1:
            return

        if self.fire_cooldown > 0:
            return

        self.fire_cooldown = 0.5
        self.engine.audio.play_sfx('assets/sounds/gunshot.mp3')
        print("[Weapon] AOE BLAST!")

        cam = self.engine.active_camera
        player_pos = self.entity.position + glm.vec3(0, 1.5, 0)
        forward = cam.front

        # Parameters for the "Long Cone"
        MAX_RANGE = 50.0
        CONE_ANGLE_RAD = glm.radians(30.0) # 30 degree spread

        hit_any = False
        
        # Scan all objects for NPCs in the cone
        for obj in self.engine.scene_objects:
            if getattr(obj, 'tag', '') != 'npc':
                continue
                
            # Calculate vector to NPC
            to_npc = obj.position - player_pos
            distance = glm.length(to_npc)
            
            if distance > MAX_RANGE:
                continue
            
            # Normalize for angle calculation
            dir_to_npc = glm.normalize(to_npc)
            cos_angle = glm.dot(forward, dir_to_npc)
            angle = math.acos(max(-1.0, min(1.0, cos_angle)))

            if angle <= CONE_ANGLE_RAD / 2.0:
                # HIT!
                if obj.alpha > 0.5:
                    print(f"[Weapon] CONE HIT NPC: {obj.name}")
                    obj.alpha = 0.5
                    self.engine.audio.play_sfx('assets/sounds/bloodGushing.mp3')
                    hit_any = True
                    
                    # Special Story Trigger (matches original behavior)
                    # We trigger this if ANY npc in the cone is "dying" and haven't already
                    if not self.engine.global_flags.get('thief_shot'):
                        self.engine.hud.set_task("A cruel realisation", "Talk to Tony")
                        self.engine.show_image_overlay('assets/transitions/act2.jpg', 3.0)
                        self.engine.global_flags['thief_shot'] = True
                        self.tp_timer = 3.0
                else:
                    print(f"[Weapon] NPC {obj.name} already hit.")

        if not hit_any:
            print("[Weapon] Blast missed everything.")

    def _import_math(self):
        import math
        return math
