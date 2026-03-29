import pybullet as p

class Trigger:
    """
    A 'Ghost' Trigger script that allows the player to walk through.
    It uses PyBullet's getClosestPoints to detect overlap without physical collision.
    """
    def start(self):
        self.triggered = False
        self.enemy_names = getattr(self.entity, 'trigger_enemies', '').split(',') if hasattr(self.entity, 'trigger_enemies') else []
        self.enemy_names = [name.strip() for name in self.enemy_names if name.strip()]
        
        # Disable physical collision resolution (no bumping)
        # We set its collision group and mask to 0 so it's ignored by the solver.
        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            phys = self.engine.physics_system
            p.setCollisionFilterGroupMask(
                body_id, -1, 0, 0, 
                physicsClientId=phys.client_id
            )

    def update(self, dt):
        if self.triggered:
            return

        # Get the player entity
        player = self.engine.interaction_manager._get_player()
        if not player or not hasattr(player, 'pybullet_body_id'):
            return

        # Check for overlap (distance <= 0)
        phys = self.engine.physics_system
        trigger_id = self.entity.pybullet_body_id
        player_id = player.pybullet_body_id

        # If the closest distance between them is 0 or less, they are overlapping
        points = p.getClosestPoints(player_id, trigger_id, distance=0.0, physicsClientId=phys.client_id)
        
        if points:
            self.triggered = True
            self.on_trigger_enter()

    def on_trigger_enter(self):
        """Logic to run when triggered."""
        for enemy_name in self.enemy_names:
            for script in self.engine.script_manager.active_scripts:
                if script.entity.name == enemy_name and hasattr(script, 'set_enabled'):
                    script.set_enabled(True)
                    break
