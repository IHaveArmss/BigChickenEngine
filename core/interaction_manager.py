"""InteractionManager — detects which interactable object the player is looking at
and dispatches on_interact() when the player presses E.

Detection requires BOTH:
  1. Player entity is within obj.interaction_distance.
  2. The object is within a cone in front of the player (player-facing direction).

When no player entity is registered, falls back to camera position + front for both checks.
"""

import glm


class InteractionManager:
    def __init__(self, engine):
        self.engine = engine
        self.hovered_object = None
        self._player = None

        # Cone half-angle thresholds (dot product)
        self._camera_dot_threshold = 0.1  # ~84 deg — used for camera-only fallback

    def set_player(self, entity):
        """Explicitly register the player entity. Call from a script's start()."""
        self._player = entity

    def _get_player(self):
        if self._player is not None and self._player in self.engine.scene_objects:
            return self._player
        player = self.engine.find_one_by_tag('player')
        if player is not None:
            self._player = player
        return self._player


    def _player_forward(self, player):
        """Return the player's horizontal forward vector from their Y rotation."""
        euler_y = glm.radians(player.rotation_euler.y)
        return glm.vec3(-glm.sin(euler_y), 0.0, -glm.cos(euler_y))

    def update(self):
        """Called once per frame in play mode. Updates hovered_object."""
        if self.engine.dialogue.active:
            return  
        
        player = self._get_player()
        cam = self.engine.active_camera
        
        if glm.length(cam.front) < 0.001:
            return

        # Proximity origin
        origin_pos = player.position if player else cam.position
        
        best, best_dist = None, float('inf')
        for obj in self.engine.scene_objects:
            if not obj.interactable:
                continue

            # 1. Proximity check
            delta = obj.position - origin_pos
            dist_to_origin = glm.length(delta)
            if dist_to_origin > obj.interaction_distance:
                continue

            # 2. Strategy-based Direction check
            is_view_mode = getattr(obj, 'use_view_interaction', False) or player is None
            
            # Hysteresis: If already hovered, make the cone more lenient to prevent flickering
            is_currently_hovered = (obj is self.hovered_object)
            
            if is_view_mode:
                # Modern camera-view gaze check (relative to camera origin for better picking)
                threshold = 0.5 if is_currently_hovered else 0.7
                delta_cam = obj.position - cam.position
                if glm.length(delta_cam) > 0.001:
                    dir_to_obj = glm.normalize(delta_cam)
                    dot = glm.dot(cam.front, dir_to_obj)
                    if dot < threshold:
                        continue
            else:
                # Classic character-facing check (horizontal)
                threshold = 0.5 if is_currently_hovered else 0.6
                player_fwd = self._player_forward(player)
                player_fwd_xz = glm.normalize(glm.vec3(player_fwd.x, 0.0, player_fwd.z))
                
                delta_xz = glm.normalize(glm.vec3(delta.x, 0.0, delta.z))
                dot = glm.dot(player_fwd_xz, delta_xz)
                if dot < threshold:
                    continue

            if dist_to_origin < best_dist:
                best_dist = dist_to_origin
                best = obj

        if self.hovered_object and self.hovered_object is not best:
            self.hovered_object.is_hovered = False
        self.hovered_object = best
        if best:
            best.is_hovered = True

    def try_interact(self):
        """Called when the player presses E. Fires on_interact() on hovered object's scripts."""
        if self.engine.dialogue.active:
            return
        if self.hovered_object:
            result = self.engine.script_manager.dispatch_interact(self.hovered_object)
            if result is not None:
                self.engine.dialogue.start(self.hovered_object, result)

    def clear(self):
        """Clear hover state and cached player — call when leaving play mode."""
        if self.hovered_object:
            self.hovered_object.is_hovered = False
        self.hovered_object = None
        self._player = None
