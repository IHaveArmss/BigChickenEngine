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
        
        # Trigger transition back to cutscene_demo, using the spawn_from_lobby marker
        self.engine.load_scene("scenes/cutscene_demo.json", target_marker="spawn_from_lobby")
        
        return None
