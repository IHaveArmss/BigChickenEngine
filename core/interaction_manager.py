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
        self._player_dot_threshold = 0.6   # ~53 deg — player must face more toward object
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

        if player is not None:
            origin_pos = player.position
            player_fwd = self._player_forward(player)
            
            # Flatten player forward to XZ plane (ignore height)
            player_fwd_xz = glm.normalize(glm.vec3(player_fwd.x, 0.0, player_fwd.z))
            dot_threshold = self._player_dot_threshold
        else:
            origin_pos = cam.position
            player_fwd_xz = None
            dot_threshold = self._camera_dot_threshold

        best, best_dist = None, float('inf')
        for obj in self.engine.scene_objects:
            if not obj.interactable:
                continue

            # 1. Proximity check
            dist_to_origin = glm.length(obj.position - origin_pos)
            if dist_to_origin < 0.001 or dist_to_origin > obj.interaction_distance:
                continue

            # 2. Direction check - use player facing with XZ flattening
            if player is not None:
                delta = obj.position - origin_pos
                # Flatten to XZ plane
                dir_xz = glm.normalize(glm.vec3(delta.x, 0.0, delta.z))
                dot = glm.dot(player_fwd_xz, dir_xz)
                
                if dot < dot_threshold:
                    continue
            else:
                # Fallback to camera direction
                delta_eye = obj.position - origin_pos
                dist_eye = glm.length(delta_eye)
                
                if dist_eye > 0.001:
                    dir_from_eye = delta_eye / dist_eye
                    dot = glm.dot(cam.front, dir_from_eye)
                    
                    if dot < dot_threshold:
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
