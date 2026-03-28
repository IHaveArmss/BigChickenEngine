class DoorGuardian:
    """
    Triggers the Hobo's appearance based on a response.
    """
    def start(self):
        # We don't need to do much here, just wait for choices
        pass

    def select_choice(self, index):
        """
        Choice 0 represents "Enter" from the NPC_Guardian's dialogue.
        """
        # If "Enter" is chosen
        if index == 0:
            print("[DoorGuardian] Choice: Enter. Unlocking Hobo trigger...")
            # Set a global "flag" so the Hobo Finder trigger can see it
            self.engine.global_flags['hobo_unlocked'] = True
        else:
            print(f"[DoorGuardian] Choice {index} selected. No action taken.")

    def summon_hobo(self):
        # Find the hobo and call its appear method
        for script in self.engine.script_manager.active_scripts:
            # Check script entity name and if it has hobo_logic attached (using appear method as signature)
            if script.entity.name == "Hobo" and hasattr(script, 'appear'):
                script.appear()
                return
        print("[DoorGuardian] WARNING: No Hobo with HoboLogic found to summon.")
