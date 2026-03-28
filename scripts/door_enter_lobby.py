class DoorEnterLobby:
    """
    Handles the transition to the lobby when the 'Enter' dialogue choice is selected.
    """
    def start(self):
        # Default target properties if not explicitly set in JSON
        if not hasattr(self.entity, 'scene_path'):
            self.entity.scene_path = "scenes/lobby.json"
        if not hasattr(self.entity, 'target_position'):
            self.entity.target_position = [-4.59, 0.674, 0.129]
        if not hasattr(self.entity, 'target_rotation'):
            self.entity.target_rotation = [180.0, 89.62, 180.0]

    def select_choice(self, index):
        """
        Choice 0 represents "Enter" from the NPC_Guardian's dialogue.
        """
        if index == 0:
            print("[DoorEnterLobby] 'Enter' selected. Transitioning to Lobby...")
            
            # Unlock the Hobo flag (legacy logic for game progression)
            self.engine.global_flags['hobo_unlocked'] = True
            
            # Read transition properties from the entity
            target = getattr(self.entity, 'scene_path', "scenes/lobby.json")
            spawn_pos = getattr(self.entity, 'target_position', None)
            spawn_rot = getattr(self.entity, 'target_rotation', None)
            
            # Snap to the new scene
            self.engine.load_scene(target, spawn_pos=spawn_pos, spawn_rot=spawn_rot)
        else:
            print(f"[DoorEnterLobby] Choice {index} ignored.")
