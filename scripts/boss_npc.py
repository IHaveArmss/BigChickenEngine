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
            # We use 'ayan_formal_sitting' which was loaded via animation_source
            self.entity.animator.play("ayan_formal_sitting", loop=True)

    def on_interact(self):
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
            print("[BossNpc] Transitioning to standing...")
            if self.entity.animator:
                # Crossfade to the standing animation (the base model's animation)
                # 'ayan_formal_standing' is usually the name because it was the base GLB
                self.entity.animator.crossfade("ayan_formal_standing", duration=0.8)
                self.state = "standing"
