import pybullet as p
import glm

class HoboFinder:
    """
    Trigger script that only fires after 'hobo_unlocked' flag is set.
    When triggered, it plays a cutscene and reveals the Hobo.
    """
    def start(self):
        self.triggered = False
        
        # Ghost mode: disable physical collision
        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            p.setCollisionFilterGroupMask(
                body_id, -1, 0, 0, 
                physicsClientId=self.engine.physics_system.client_id
            )
        print(f"[HoboFinder] Ready. Waiting for unlock...")

    def update(self, dt):
        if self.triggered:
            return

        # ONLY proceed if the 'hobo_unlocked' flag is set (after talking to the Door Guardian)
        if not self.engine.global_flags.get('hobo_unlocked', False):
            return

        # Check for overlap with player
        player = self.engine.interaction_manager._get_player()
        if not player or not hasattr(player, 'pybullet_body_id'):
            return

        phys = self.engine.physics_system
        trigger_id = self.entity.pybullet_body_id
        player_id = player.pybullet_body_id

        points = p.getClosestPoints(player_id, trigger_id, distance=0.0, physicsClientId=phys.client_id)
        
        if points:
            self.triggered = True
            self.on_trigger_enter()

    def on_trigger_enter(self):
        print(f"[HoboFinder] Triggered! Playing 'hobo_find' cutscene...")
        
        # 1. Play the cutscene
        if self.engine.cutscenes.load('hobo_find'):
            self.engine.cutscenes.play()
        
        # 2. Summon the Hobo
        self.summon_hobo()

    def summon_hobo(self):
        found = False
        for script in self.engine.script_manager.active_scripts:
            if script.entity.name == "Hobo" and hasattr(script, 'appear'):
                script.appear()
                found = True
        
        if not found:
             print("[HoboFinder] WARNING: Could not find Hobo script to reveal.")
