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
        
        # Check if we should use the Pose transform or the Original transform
        has_pose = False
        if self.entity.animator:
            # Check if the desired pose clip exists in the animator's animations
            if hasattr(self.entity.animator, 'animations'):
                # Handle case-insensitive check if needed, but standard lookup first
                if self.pose_anim in self.entity.animator.animations:
                    has_pose = True
                else:
                    # Fallback case-insensitive check
                    for k in self.entity.animator.animations.keys():
                        if k.lower() == self.pose_anim.lower():
                            has_pose = True
                            break

        if has_pose:
            print(f"[ThiefLogic] Pose '{self.pose_anim}' found. Applying pose transform.")
            # Set Rotation and Scale for the Pose (Hands on back)
            self.entity.set_rotation_euler(90.0, -90.0, 0.0)
            self.entity.scale = glm.vec3(0.067, 0.042, 0.046)
            self.entity.animator.play(self.pose_anim, loop=True)
        else:
            print(f"[ThiefLogic] Pose '{self.pose_anim}' NOT found! Falling back to original transform.")
            # Set Rotation and Scale for the Original/Static mesh
            self.entity.set_rotation_euler(9.0, -90.0, 0.0)
            self.entity.scale = glm.vec3(5.239, 3.274, 3.585)

        self.entity._physics_dirty = True
        print(f"[ThiefLogic] {self.entity.name} has appeared (alpha only)!")
