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
        # Check if already triggered in a past visit to this scene
        if self.engine.global_flags.get('hobo_found', False):
            self.triggered = True
            # Make sure the Hobo is revealed immediately if returning to the scene
            self.summon_hobo()
            print(f"[HoboFinder] Hobo already found. Skipping trigger.")
        else:
            print(f"[HoboFinder] Ready. Waiting for unlock...")

    def update(self, dt):
        # Trigger 'Hero for today' task once the discovering cutscene ends
        if self.triggered and not self.engine.cutscenes.is_playing and not self.engine.global_flags.get('task_hero_today_set'):
            self.engine.hud.set_task("Hero for today", "Help the injured man")
            self.engine.global_flags['task_hero_today_set'] = True

        if self.triggered:
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
        # Mark as persistent 'found' so it never plays again
        self.engine.global_flags['hobo_found'] = True
        
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
