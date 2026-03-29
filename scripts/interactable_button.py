class InteractableButton:
    """
    A script for objects that the player can interact with by pressing 'E'.
    To use:
    1. Attach this script to an object.
    2. Ensure 'Interactable' is checked in the Property Panel.
    """
    def start(self):
        print(f"[Button] Interactable button ready on {self.entity.name}")

    def on_interact(self):
        """Called when the player presses E while looking at this object."""
        print(f"[Button] Interaction triggered on {self.entity.name}!")
        
        # Determine target scene from entity property, default to lobby_act3
        target_scene = getattr(self.entity, 'scene_path', "scenes/lobby_act3.json")
        target_marker = getattr(self.entity, 'target_marker', None)
        
        print(f"[Button] Transitioning to {target_scene}...")
        self.engine.load_scene(target_scene, target_marker=target_marker)
        
        return None
