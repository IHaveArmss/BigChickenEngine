class InterogDoorLogic:
    """
    Special logic for the interrogation room door in Act 2.
    Currently set to do nothing as per instruction.
    """
    def start(self):
        print(f"[InterogDoor] Script ready on {self.entity.name}")

    def on_interact(self):
        """Called when the player presses E on the door."""
        print("[InterogDoor] You interacted with the door, but it's currently locked or disabled.")
        # Future logic goes here!
        return None
