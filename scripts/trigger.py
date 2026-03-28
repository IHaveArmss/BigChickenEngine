import pybullet as p

class Trigger:
    """
    A 'Ghost' Trigger script that allows the player to walk through.
    It uses PyBullet's getClosestPoints to detect overlap without physical collision.
    """
    def start(self):
        self.triggered = False
        
        # Disable physical collision resolution (no bumping)
        # We set its collision group and mask to 0 so it's ignored by the solver.
        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            phys = self.engine.physics_system
            p.setCollisionFilterGroupMask(
                body_id, -1, 0, 0, 
                physicsClientId=phys.client_id
            )
            
        print(f"[Trigger] Ghost mode active on {self.entity.name}")

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
        print(f"[Trigger] Player entered {self.entity.name}! (One-time trigger)")
