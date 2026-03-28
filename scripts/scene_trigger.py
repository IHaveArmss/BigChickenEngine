class SceneTrigger:
    """
    A script for teleporters or doors that change the scene when interacted with.
    Usage:
    - Attach this script to an object.
    - Set 'scene_path' in the JSON properties (e.g., 'scenes/pizza.json').
    """
    def start(self):
        # Default target if none specified in JSON
        if not hasattr(self.entity, 'scene_path'):
            self.entity.scene_path = "scenes/pizza.json"
        
        print(f"[SceneTrigger] Ready on {self.entity.name}. Target: {self.entity.scene_path}")

    def on_interact(self):
        """Called when the player presses E while looking at this object."""
        target = getattr(self.entity, 'scene_path', "scenes/pizza.json")
        spawn_pos = getattr(self.entity, 'target_position', None)
        spawn_rot = getattr(self.entity, 'target_rotation', None)
        
        print(f"[SceneTrigger] Changing scene to: {target}")
        
        # Trigger the engine-level scene load
        self.engine.load_scene(target, spawn_pos=spawn_pos, spawn_rot=spawn_rot)
        return None
