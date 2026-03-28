import glm

class ThiefLogic:
    """
    Handles the Thief's appearance with hardcoded coordinates to ensure
    the 'reset' works even if the scene is saved in the editor.
    """
    def start(self):
        # Hardcoded 'Appear' State
        self.dest_pos = glm.vec3(-11.63, 4.36, -4.72)
        self.dest_rot = glm.vec3(90.0, -89.972, 0.0)
        self.dest_alpha = 1.0
        
        # Force initial 'Hidden' State every time game boots
        self.hide()

    def hide(self):
        self.entity.position.y = -500.0
        self.entity.alpha = 0.0 # Force initial opacity 0 as requested
        self.entity.is_collideable = False
        self.entity._physics_dirty = True
        print(f"[ThiefLogic] {self.entity.name} is now hidden.")

    def appear(self):
        self.entity.position = glm.vec3(self.dest_pos)
        self.entity.set_rotation_euler(self.dest_rot.x, self.dest_rot.y, self.dest_rot.z)
        self.entity.alpha = self.dest_alpha
        self.entity.is_collideable = True
        self.entity._physics_dirty = True
        print(f"[ThiefLogic] {self.entity.name} has appeared (Save-Proof Reset)!")
