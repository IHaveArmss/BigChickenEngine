import glm

class HoboLogic:
    """
    Handles the Hobo's appearance with hardcoded coordinates to ensure
    the 'reset' works even if the scene is saved in the editor.
    """
    def start(self):
        # Hardcoded 'Appear' State
        self.dest_pos = glm.vec3(-21.87, 4.55, -2.48)
        self.dest_rot = glm.vec3(0.0, -9.0, 0.0)
        self.dest_alpha = 1.0
        
        # Force initial 'Hidden' State every time game boots
        self.hide()

    def hide(self):
        self.entity.position.y = -500.0
        self.entity.alpha = 0.0
        self.entity.is_collideable = False
        self.entity._physics_dirty = True
        print(f"[HoboLogic] {self.entity.name} is now hidden.")

    def appear(self):
        self.entity.position = glm.vec3(self.dest_pos)
        self.entity.set_rotation_euler(self.dest_rot.x, self.dest_rot.y, self.dest_rot.z)
        self.entity.alpha = self.dest_alpha
        self.entity.is_collideable = True
        self.entity._physics_dirty = True
        print(f"[HoboLogic] {self.entity.name} has appeared (Save-Proof Reset)!")

    def select_choice(self, index):
        print(f"[HoboLogic] Choice {index} made. Summoning Thief...")
        self.summon_thief()

    def summon_thief(self):
        for script in self.engine.script_manager.active_scripts:
            if script.entity.name == "Thief" and hasattr(script, 'appear'):
                script.appear()
                return
        print("[HoboLogic] WARNING: No Thief found to summon.")
