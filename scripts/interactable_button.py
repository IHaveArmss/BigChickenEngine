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
        
        # Example: Pulse the color when pressed
        if hasattr(self.entity, 'meshes') and self.entity.meshes:
            # You can add logic here, like opening a door or starting a cutscene
            pass
            
        # Return a string if you want to trigger a dialogue alongside the action:
        # return "You pressed the button!"
        return None
