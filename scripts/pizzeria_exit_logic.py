class PizzeriaExitLogic:
    """
    Handles the transition out of the Pizzeria.
    Branching Logic:
    - If thief_shot is True: Go to Act 2 (world ruins).
    - Else: Go back to the Cutscene Demo scene (original town).
    """
    def start(self):
        print(f"[PizzeriaExit] Logic active on {self.entity.name}")

    def on_interact(self):
        """Called when the player presses E on the pizzeria door."""
        # Check the global flag set in weapon.py when the thief is killed
        thief_shot = self.engine.global_flags.get('thief_shot', False)
        
        if thief_shot:
            print("[PizzeriaExit] Branch detected: Thief was shot. Loading ACT 2...")
            # Load Act 2 using the specific marker I just added
            self.engine.load_scene("scenes/act2.json", target_marker="spawn_player_act2")
        else:
            print("[PizzeriaExit] Default branch: Thief alive. Loading Town...")
            # Use the specific spawn_from_pizza marker requested
            self.engine.load_scene("scenes/cutscene_demo.json", target_marker="spawn_from_pizza")
            
        return None
