import glm
import math

class NPC:
    """
    Dynamic NPC script with 'Look At Player' focus.
    Returns dialogue data set via the Editor's NPC Dialogue section.
    """
    def start(self):
        # NPCs are interactable by default
        self.entity.interactable = True
        if not hasattr(self.entity, 'dialogue_data'):
            self.entity.dialogue_data = None

    def on_interact(self):
        # 1. Focus: Rotate to face the player/camera
        player = self.engine.interaction_manager._get_player()
        target_pos = player.position if player else self.engine.active_camera.position
        
        # Calculate direction on XZ plane (ignore pitch)
        diff = target_pos - self.entity.position
        if glm.length(glm.vec3(diff.x, 0, diff.z)) > 0.01:
            # Standard atan2 for Y-up coordination systems
            angle_rad = math.atan2(-diff.x, -diff.z)
            self.entity.rotation_euler.y = math.degrees(angle_rad)
            self.entity._physics_dirty = True
            
        # 2. Return the dynamic dialogue data from the editor
        data = getattr(self.entity, 'dialogue_data', None)
        if not data:
            return {
                "start_node": "none",
                "nodes": {
                    "none": {"speaker": self.entity.name, "text": "I have nothing to say...", "next": "exit"},
                    "exit": {"text": ""}
                }
            }
        return data
