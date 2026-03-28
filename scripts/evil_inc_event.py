import pybullet as p
import glm
import time

class EvilIncEvent:
    """
    Evil Inc Event Script:
    1. Triggers cutscene 'evil_inc_cut.json' when player enters.
    2. Waits for cutscene to finish.
    3. Finds object with tag 'redThunder', makes it visible (alpha 1.0).
    4. Plays 'assets/sounds/thunderClab1.mp3'.
    """
    def start(self):
        self.state = "WAITING"
        self.timer = 0.0
        self.freeze_cam = None
        self.played = False
        self.saved_cam = None
        
        # Disable physics collision so player can walk through the trigger
        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            phys = self.engine.physics_system
            p.setCollisionFilterGroupMask(body_id, -1, 0, 0, physicsClientId=phys.client_id)
            
        print(f"[EvilInc] Ready on {self.entity.name}")

    def update(self, dt):
        if self.state == "DONE":
            return

        if self.state == "WAITING":
            # Continuously try to capture the player camera as soon as it's set by ThirdPerson/PlayerController
            if self.saved_cam is None and self.engine.play_camera is not None:
                self.saved_cam = self.engine.play_camera
            
            if self.played:
                return

            # Check for player overlap
            player = self.engine.interaction_manager._get_player()
            if not player or not hasattr(player, 'pybullet_body_id'):
                return

            phys = self.engine.physics_system
            trigger_id = getattr(self.entity, 'pybullet_body_id', None)
            player_id = player.pybullet_body_id
            
            if trigger_id is None:
                return

            points = p.getClosestPoints(player_id, trigger_id, distance=0.0, physicsClientId=phys.client_id)
            if points:
                print("[EvilInc] Player entered trigger! Starting once-only sequence.")
                self.played = True
                # Final attempt to capture camera if we haven't yet
                if self.saved_cam is None:
                    self.saved_cam = self.engine.play_camera
                self.start_cutscene()

        elif self.state == "PLAYING":
            # Wait for cutscene to finish
            if not self.engine.cutscenes.is_playing:
                print("[EvilInc] Cutscene path finished. Locking camera for exactly 3 seconds.")
                
                # Capture exact final waypoint for the freeze
                if self.engine.cutscenes.waypoints:
                    from core.camera import Camera
                    wp = self.engine.cutscenes.waypoints[-1]
                    self.freeze_cam = Camera(position=glm.vec3(wp["pos"]), 
                                            yaw=wp["yaw"], pitch=wp["pitch"])
                    self.engine.set_play_camera(self.freeze_cam)
                
                # Strike IMMEDIATELY
                self.trigger_thunder(True)
                
                self.timer = 0.0
                self.has_hidden = False
                self.state = "FREEZING"

        elif self.state == "FREEZING":
            self.timer += dt
            
            # FORCE camera lock every frame for 3 seconds
            if self.freeze_cam:
                self.engine.set_play_camera(self.freeze_cam)
            
            # After 1 second, hide the thunder sprite
            if self.timer >= 1.0 and not self.has_hidden:
                print("[EvilInc] Hiding lightning.")
                self.trigger_thunder(False)
                self.has_hidden = True
            
            # After 3 total seconds, fully return camera and controls to player
            if self.timer >= 3.0:
                print("[EvilInc] Sequence complete. Returning control to player.")
                
                # Restore the player's specific camera (e.g. ThirdPerson camera)
                if self.saved_cam:
                    self.engine.set_play_camera(self.saved_cam)
                else:
                    # Defensive fallback: search for a camera on the player object
                    player = self.engine.interaction_manager._get_player()
                    p_cam = None
                    if player:
                        # Look for ThirdPerson or similar script that has a 'camera' attribute
                        for s in self.engine.script_manager.active_scripts:
                            if s.entity == player and hasattr(s, 'camera'):
                                p_cam = s.camera
                                break
                    
                    if p_cam:
                        print("[EvilInc] Recovered player camera from script.")
                        self.engine.set_play_camera(p_cam)
                    else:
                        print("[EvilInc] WARNING: Could not find player camera to restore!")
                        self.engine.set_play_camera(None)
                
                self.engine.cutscenes.can_player_move = True
                self.state = "DONE"

    def start_cutscene(self):
        if self.engine.cutscenes.load("evil_inc_cut"):
            self.engine.cutscenes.play()
            self.state = "PLAYING"
        else:
            print("[EvilInc] ERROR: Could not load assets/cutscenes/evil_inc_cut.json")
            self.trigger_thunder(True)
            self.state = "DONE"

    def trigger_thunder(self, visible):
        # Find the thunder sprite by tag
        thunder_obj = self.engine.find_one_by_tag("redThunder")
        if thunder_obj:
            thunder_obj.alpha = 1.0 if visible else 0.0
            if visible:
                print(f"[EvilInc] Found {thunder_obj.name}, flash!")
        
        if visible:
            self.engine.audio.play_sfx("assets/sounds/thunderClap1.mp3")
