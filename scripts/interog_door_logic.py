class InterogDoorLogic:
    """
    Special logic for the interrogation room door in Act 2.
    Loads the target scene when interacted with.
    """
    def start(self):
        print(f"[InterogDoor] Script ready on {self.entity.name}")

    def on_interact(self):
        """Called when the player presses E on the door."""
        target = getattr(self.entity, 'scene_path', 'scenes/warehouse.json')
        spawn_pos = getattr(self.entity, 'target_position', None)
        spawn_rot = getattr(self.entity, 'target_rotation', None)

        print(f"[InterogDoor] Changing scene to: {target}")
        self.engine.load_scene(target, spawn_pos=spawn_pos, spawn_rot=spawn_rot)
        return None
