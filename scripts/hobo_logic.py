import glm

class HoboLogic:
    """
    Handles the Hobo's appearance with hardcoded coordinates to ensure
    the 'reset' works even if the scene is saved in the editor.
    """
    def start(self):
        # Determine if we should start hidden
        if not self.engine.global_flags.get('hobo_found', False):
            self.hide()
        else:
            self.appear()

    def hide(self):
        self.entity.alpha = 0.0
        self.entity.is_collideable = False
        print(f"[HoboLogic] {self.entity.name} is now hidden (alpha only).")

    def appear(self):
        self.entity.alpha = 1.0
        self.entity.is_collideable = True
        print(f"[HoboLogic] {self.entity.name} has appeared (alpha only)!")

    def on_interact(self):
        # Face the player/camera when talking
        player = self.engine.interaction_manager._get_player()
        target_pos = player.position if player else self.engine.active_camera.position
        
        diff = target_pos - self.entity.position
        if glm.length(glm.vec3(diff.x, 0, diff.z)) > 0.01:
            import math
            angle_rad = math.atan2(-diff.x, -diff.z)
            self.entity.set_rotation_euler(0.0, math.degrees(angle_rad), 0.0)
            self.entity._physics_dirty = True
            
        return getattr(self.entity, 'dialogue_data', None)

    def on_dialogue_action(self, action_name):
        """Called by DialogueManager for trigger nodes like 'summon_thief'"""
        if action_name == "summon_thief":
            print(f"[HoboLogic] Action '{action_name}' triggered. Summoning Thief...")
            self.engine.hud.set_task("Hero?", "Defend yourself (F for gun)")
            self.summon_thief()

    def summon_thief(self):
        for script in self.engine.script_manager.active_scripts:
            # We look for the Thief script by name
            if script.entity.name == "Thief" and hasattr(script, 'appear'):
                script.appear()
                return
        print("[HoboLogic] WARNING: No Thief found to summon.")
