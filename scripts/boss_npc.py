import glm
import math

class BossNpc:
    """
    Boss NPC script: handles a sitting-to-standing transition.
    """
    def start(self):
        # NPCs are interactable by default
        self.entity.interactable = True
        self.state = "sitting"
        
        # Start sitting
        if self.entity.animator:
            # New format: filename|clipname (avoids collision for Mixamo assets)
            self.entity.animator.play("ayan_formal_sitting|Armature|mixamo.com|Layer0", loop=True)

    def on_interact(self):
        # Set the custom boss voice lines for this interaction 
        # (DialogueManager now handles the random selection)
        self.engine.dialogue.talk_sounds = [
            "assets/sounds/bossvoice1.mp3",
            "assets/sounds/bossvoice2.mp3",
            "assets/sounds/bossvoice3.mp3",
        ]

        # 1. Focus: Rotate to face the player/camera (Only if standing)
        if self.state == "standing":
            player = self.engine.interaction_manager._get_player()
            target_pos = player.position if player else self.engine.active_camera.position
            
            diff = target_pos - self.entity.position
            if glm.length(glm.vec3(diff.x, 0, diff.z)) > 0.01:
                angle_rad = math.atan2(-diff.x, -diff.z)
                self.entity.set_rotation_euler(0.0, math.degrees(angle_rad), 0.0)
                self.entity._physics_dirty = True
            
        # 2. Return dialogue data
        return getattr(self.entity, 'dialogue_data', None)

    def on_dialogue_action(self, action_name):
        """Triggered by the dialogue system: {"action": "stand_up"}"""
        if action_name == "stand_up" and self.state == "sitting":
            print(f"[BossNpc] STAND UP TRIGGERED for {self.entity.name}")
            if self.entity.animator:
                # The external clip is named 'ayan_formal_standing' in the animator
                anim_name = "ayan_formal_standing"
                print(f"[BossNpc] Crossfading to '{anim_name}'...")
                self.entity.animator.crossfade(anim_name, duration=0.8)
                self.state = "standing"
                
            # Find the teleport target marker
            target_name = "boss_after_dialogue"
            target = self.engine.get_object_by_name(target_name)
            if target:
                print(f"[BossNpc] Found '{target_name}' at {target.position}. Teleporting...")
                # Move to the position of the marker, but DO NOT take its rotation
                self.entity.position = target.position
                self.entity._physics_dirty = True
                print(f"[BossNpc] '{self.entity.name}' position now: {self.entity.position}")
            else:
                print(f"[BossNpc] WARNING: '{target_name}' entity not found in engine!")
    def on_shot(self):
        """Triggered by weapon.py when this specific NPC is hit by the blast."""
        print(f"[BossNpc] {self.entity.name} WAS SHOT! Triggering ending...")
        
        # 1. Audiovisual feedback
        self.engine.audio.play_sfx('assets/sounds/bloodGushing.mp3')
        
        # 2. Cut to black (User requested persistent, so 999s)
        self.engine.show_image_overlay('assets/transitions/black.png', 999.0)
        
        # 3. Set a timer for the dialogue (starts in update, user requested 3s)
        self.ending_dialogue_timer = 3.0
        self.state = "ending"

    def update(self, dt):
        """Standard update loop."""
        if hasattr(self, 'ending_dialogue_timer') and self.ending_dialogue_timer > 0:
            self.ending_dialogue_timer -= dt
            if self.ending_dialogue_timer <= 0:
                print("[BossNpc] Starting ending dialogue...")
                # Get the dialogue data from the entity
                data = getattr(self.entity, 'dialogue_data', None)
                if data:
                    # Manually override the starting node so we skip the intro
                    data["start_node"] = "phone_ending"
                    self.engine.dialogue.start(self.entity, data)
                else:
                    print("[BossNpc] ERROR: No dialogue_data found on entity!")
