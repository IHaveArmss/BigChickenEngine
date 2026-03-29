import glm

class ThiefLogic:
    """
    Handles the Thief's appearance with hardcoded coordinates to ensure
    the 'reset' works even if the scene is saved in the editor.
    """
    def start(self):
        # Mixamo-style pose animation name
        self.pose_anim = "dennis_formal_standing|Armature|mixamo.com|Layer0"
        
        # Start hidden
        self.hide()

    def hide(self):
        self.entity.alpha = 0.0 
        self.entity.is_collideable = False
        if self.entity.animator:
            self.entity.animator.stop()
        print(f"[ThiefLogic] {self.entity.name} is now hidden (alpha only).")

    def appear(self):
        self.entity.alpha = 1.0
        self.entity.is_collideable = True
        
        # Pose the character correctly (fixes T-posing)
        if self.entity.animator:
            print(f"[ThiefLogic] Playing pose: {self.pose_anim}")
            self.entity.animator.play(self.pose_anim, loop=True)
            
        print(f"[ThiefLogic] {self.entity.name} has appeared (alpha only)!")
