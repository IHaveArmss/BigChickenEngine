class InteractableButton:
    """
    A script for objects that the player can interact with by pressing 'E'.
    To use:
    1. Attach this script to an object.
    2. Ensure 'Interactable' is checked in the Property Panel.
    """
    def start(self):
        print(f"[Button] Interactable button ready on {self.entity.name}")
        if not hasattr(self.entity, 'scene_path'):
            self.entity.scene_path = "scenes/lobby_act3.json"

    def on_interact(self):
        """Called when the player presses E while looking at this object."""
        print(f"[Button] Interaction triggered on {self.entity.name}!")

        dialogue_data = getattr(self.entity, 'dialogue_data', None)
        if dialogue_data:
            return dialogue_data

        target_scene = getattr(self.entity, 'scene_path', "scenes/lobby_act3.json")
        target_marker = getattr(self.entity, 'target_marker', None)

        print(f"[Button] Transitioning to {target_scene}...")
        self.engine.load_scene(target_scene, target_marker=target_marker)

        return None

    def select_choice(self, index):
        target_scene = getattr(self.entity, 'scene_path', "scenes/lobby_act3.json")
        target_marker = getattr(self.entity, 'target_marker', None)

        print(f"[Button] Dialogue choice {index} selected on {self.entity.name}. Transitioning to {target_scene}...")
        self.engine.load_scene(target_scene, target_marker=target_marker)
