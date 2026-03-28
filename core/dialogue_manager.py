"""DialogueManager — camera zoom-in dialogue with text, branching choices, and state memory.

Scripts return dialogue data from on_interact() using either:

OLD FORMAT (still supported for backwards compatibility):
    return [
        {"speaker": "Guard", "text": "Hello!", "choices": [...]},
    ]

NEW FORMAT (recommended):
    return {
        "start_node": "greeting",
        "nodes": {
            "greeting": {
                "speaker": "Guard",
                "text": "Hello traveler!",
                "choices": [
                    {"text": "Who are you?", "next": "identity"},
                    {"text": "Goodbye.", "next": "exit"},
                ]
            },
            "identity": {
                "speaker": "Guard",
                "text": "I am the guard.",
                "next": "exit",
            }
        }
    }

Features:
- String-based node IDs instead of integer indices
- "requires" condition to hide choices based on global_flags
- "set_flag" action to set global_flags when choosing
- "action" callback to trigger script functions
"""

import pygame
import glm
import math


class DialogueManager:
    def __init__(self, engine):
        self.engine = engine
        self.active = False

        # Dialogue content - supports both old (list) and new (dict) formats
        self._nodes_dict = None  # New format: {node_id: node_data}
        self._current_node_id = None  # New format: current node ID
        self._is_new_format = False
        
        # Old format support
        self._lines = []
        self._index = 0
        
        self._target = None
        self._speaker = ""
        self._current_text = ""
        self._choices = None
        self._selected_choice = 0

        # Talking sounds — scripts can set this before dialogue starts
        self.talk_sounds = []
        self._talk_sound_idx = 0

        # Camera zoom
        self._saved_cam_pos = glm.vec3(0)
        self._saved_cam_front = glm.vec3(0, 0, -1)
        self._saved_cam_right = glm.vec3(1, 0, 0)
        self._saved_cam_up = glm.vec3(0, 1, 0)
        self._dialogue_cam_pos = glm.vec3(0)
        self._dialogue_cam_front = glm.vec3(0, 0, -1)
        self._zoom_progress = 0.0
        self._zoom_speed = 2.5
        self._returning = False
        # Reference to the player/third-person camera (separate from active_camera
        # which is hijacked during dialogue). Used to track live player cam position.
        self._play_cam = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, target, dialogue_data):
        """Begin dialogue.
        
        *target* is the SceneObject.
        *dialogue_data* can be either:
          - List (old format): [{"text": "..."}]
          - Dict (new format): {"start_node": "id", "nodes": {...}}
        """
        if not dialogue_data:
            return
        
        self.active = True
        self._target = target
        self._returning = False
        self._zoom_progress = 0.0
        self._talk_sound_idx = 0

        # Check which format we're using
        if isinstance(dialogue_data, dict) and "nodes" in dialogue_data:
            self._is_new_format = True
            self._nodes_dict = dialogue_data["nodes"]
            start_id = dialogue_data.get("start_node", list(self._nodes_dict.keys())[0])
        else:
            self._is_new_format = False
            self._lines = dialogue_data if isinstance(dialogue_data, list) else []
            self._index = 0

        # Snapshot current camera and remember it as the live player camera so
        # we can track its position during the return transition.
        cam = self.engine.active_camera
        self._play_cam = cam
        self._saved_cam_pos = glm.vec3(cam.position)
        self._saved_cam_front = glm.vec3(cam.front)
        self._saved_cam_right = glm.vec3(cam.right)
        self._saved_cam_up = glm.vec3(cam.up)

        # ---- Dialogue camera position & direction (manual only) ----
        #
        # Set in scene JSON on the NPC object:
        #   "dialogue_cam_pos": [x, y, z]  — world-space camera position
        #   "dialogue_cam_yaw": float       — horizontal angle in degrees (0=+X, 90=+Z, 180/-180=-X, 270/-90=-Z)
        #   "dialogue_cam_pitch": float     — vertical angle in degrees (+= look up, -= look down)
        #
        # If not set the camera stays exactly where it is.

        explicit_pos   = getattr(target, 'dialogue_cam_pos', None)
        explicit_yaw   = getattr(target, 'dialogue_cam_yaw', None)
        explicit_pitch = getattr(target, 'dialogue_cam_pitch', None)

        # Camera position — stay put if not manually set
        self._dialogue_cam_pos = glm.vec3(explicit_pos) if explicit_pos is not None else glm.vec3(cam.position)

        # Camera direction — derive front vector from yaw/pitch, or keep current
        if explicit_yaw is not None or explicit_pitch is not None:
            yaw_rad   = math.radians(explicit_yaw   or 0.0)
            pitch_rad = math.radians(explicit_pitch or 0.0)
            self._dialogue_cam_front = glm.normalize(glm.vec3(
                math.cos(yaw_rad) * math.cos(pitch_rad),
                math.sin(pitch_rad),
                math.sin(yaw_rad) * math.cos(pitch_rad),
            ))
        else:
            self._dialogue_cam_front = glm.vec3(cam.front)

        # Navigate to first node
        if self._is_new_format:
            self._advance_to_node(start_id)
        else:
            self._advance_to(0)

    def advance(self):
        """Move to the next dialogue line (E / Enter)."""
        if self._choices is not None or self._returning:
            return
        
        if self._is_new_format:
            # In new format, check if current node has a "next" field
            if self._current_node_id and self._current_node_id in self._nodes_dict:
                node = self._nodes_dict[self._current_node_id]
                next_id = node.get("next", "exit")
                self._advance_to_node(next_id)
            else:
                self._begin_end()
        else:
            self._advance_to(self._index + 1)

    def move_selection(self, delta):
        """Move the highlighted choice up (-1) or down (+1)."""
        if self._choices is None:
            return
        self._selected_choice = (self._selected_choice + delta) % len(self._choices)

    def confirm_selection(self):
        """Confirm the currently highlighted choice."""
        if self._choices is not None:
            self.select_choice(self._selected_choice)

    def select_choice(self, choice_index):
        """Pick a numbered choice (keys 1-4)."""
        if self._choices is None:
            return
        if choice_index < 0 or choice_index >= len(self._choices):
            return
        
        choice = self._choices[choice_index]
        
        # Handle set_flag actions (new format)
        if "set_flag" in choice:
            for k, v in choice["set_flag"].items():
                self.engine.global_flags[k] = v
        
        # Handle action callbacks (new format)
        if "action" in choice and self._target:
            self.engine.script_manager.dispatch_dialogue_action(self._target, choice["action"])
        
        # Dispatch to script (for backwards compatibility)
        if self._target is not None:
            self.engine.script_manager.dispatch_choice(self._target, choice_index)
        
        # Navigate to next node
        if self._is_new_format:
            next_id = choice.get("next", "exit")
            self._advance_to_node(next_id)
        else:
            next_idx = choice.get("next", self._index + 1)
            self._advance_to(next_idx)

    # ------------------------------------------------------------------
    # Per-frame update (camera lerp)
    # ------------------------------------------------------------------

    def update(self, dt):
        if not self.active:
            return

        self._zoom_progress = min(1.0, self._zoom_progress + dt * self._zoom_speed)
        t = self._smoothstep(self._zoom_progress)

        cam = self.engine.active_camera

        if not self._returning:
            # Zoom in to dialogue camera position
            cam.position = glm.mix(self._saved_cam_pos, self._dialogue_cam_pos, t)

            # Blend toward the target direction
            blended = glm.normalize(glm.mix(self._saved_cam_front, self._dialogue_cam_front, t))
            cam.front = blended
            cam.right = glm.normalize(glm.cross(blended, glm.vec3(0, 1, 0)))
            cam.up    = glm.normalize(glm.cross(cam.right, blended))
        else:
            # Keep return target in sync with the live third-person camera so we
            # always return to wherever the player camera currently is.
            if self._play_cam is not None and self._play_cam is not cam:
                self._saved_cam_pos   = glm.vec3(self._play_cam.position)
                self._saved_cam_front = glm.vec3(self._play_cam.front)
                self._saved_cam_right = glm.vec3(self._play_cam.right)
                self._saved_cam_up    = glm.vec3(self._play_cam.up)

            cam.position = glm.mix(self._dialogue_cam_pos, self._saved_cam_pos, t)

            cam.front = glm.normalize(glm.mix(self._dialogue_cam_front, self._saved_cam_front, t))
            cam.right = glm.normalize(glm.cross(cam.front, glm.vec3(0, 1, 0)))
            cam.up    = glm.normalize(glm.cross(cam.right, cam.front))

            if self._zoom_progress >= 1.0:
                cam.position = glm.vec3(self._saved_cam_pos)
                cam.front    = glm.vec3(self._saved_cam_front)
                cam.right    = glm.vec3(self._saved_cam_right)
                cam.up       = glm.vec3(self._saved_cam_up)
                self._finish()
                return

    # ------------------------------------------------------------------
    # Drawing (called from HUD._build_surface)
    # ------------------------------------------------------------------

    def draw(self, surface, font_large, font_small, win_size):
        if not self.active or not self._current_text:
            return

        cam = self.engine.active_camera
        anchor = glm.vec3(self._target.position) + glm.vec3(0, 1.0, 0)
        screen_pos = self._world_to_screen(anchor, cam, win_size)

        if screen_pos is None:
            screen_pos = (win_size[0] // 2, win_size[1] // 2)

        box_w = 480
        pad = 14
        line_h = 22

        body_lines = self._word_wrap(self._current_text, font_small, box_w - pad * 2)

        header_h = 30 if self._speaker else 0
        body_h = len(body_lines) * line_h
        choices_h = 0
        if self._choices:
            choices_h = len(self._choices) * line_h + 8
        else:
            choices_h = line_h + 4
        box_h = pad + header_h + body_h + choices_h + pad

        box_x = screen_pos[0] + 50
        box_y = screen_pos[1] - box_h // 2
        
        if box_x + box_w > win_size[0] - 10:
            box_x = screen_pos[0] - box_w - 50
        box_x = max(10, box_x)
        box_y = max(10, min(box_y, win_size[1] - box_h - 10))

        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((15, 15, 25, 210))
        pygame.draw.rect(bg, (0, 200, 120, 180), bg.get_rect(), 2, border_radius=6)
        surface.blit(bg, (box_x, box_y))

        y = box_y + pad

        if self._speaker:
            name_surf = font_large.render(self._speaker, True, (0, 220, 120))
            surface.blit(name_surf, (box_x + pad, y))
            y += header_h

        for line in body_lines:
            txt = font_small.render(line, True, (230, 230, 230))
            surface.blit(txt, (box_x + pad, y))
            y += line_h

        y += 6

        if self._choices:
            for i, ch in enumerate(self._choices):
                if i == self._selected_choice:
                    color = (255, 255, 100)
                    prefix = "> "
                else:
                    color = (180, 180, 180)
                    prefix = "  "
                txt = font_small.render(f"{prefix}{i + 1}. {ch['text']}", True, color)
                surface.blit(txt, (box_x + pad, y))
                y += line_h
        else:
            txt = font_small.render("[E] Continue", True, (120, 120, 120))
            surface.blit(txt, (box_x + pad, y))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _play_next_talk_sound(self):
        if self.talk_sounds:
            path = self.talk_sounds[self._talk_sound_idx % len(self.talk_sounds)]
            self._talk_sound_idx += 1
            self.engine.audio.play_sfx(path)

    def _advance_to_node(self, node_id):
        """Advance to a node by string ID (new format)."""
        if node_id == "exit" or node_id not in self._nodes_dict:
            self._begin_end()
            return

        self._current_node_id = node_id
        node = self._nodes_dict[node_id]
        self._speaker = node.get("speaker", "")
        self._current_text = node.get("text", "")
        if self._speaker and "choices" not in node:
            self._play_next_talk_sound()
        
        # Reset choices first
        self._choices = None
        
        # Process choices with condition filtering
        if "choices" in node:
            filtered_choices = []
            for ch in node["choices"]:
                # Check "requires" condition
                if "requires" in ch:
                    req = ch["requires"]
                    for req_key, req_val in req.items():
                        if self.engine.global_flags.get(req_key) != req_val:
                            break
                    else:
                        filtered_choices.append(ch)
                else:
                    filtered_choices.append(ch)
            
            if filtered_choices:
                self._choices = filtered_choices
                self._selected_choice = 0

    def _advance_to(self, index):
        """Advance to a node by index (old format)."""
        if index < 0 or index >= len(self._lines):
            self._begin_end()
            return
        self._index = index
        node = self._lines[index]
        self._speaker = node.get("speaker", "")
        self._current_text = node.get("text", "")
        if self._speaker and "choices" not in node:
            self._play_next_talk_sound()
        self._choices = None
        if "choices" in node:
            self._choices = node["choices"]
            self._selected_choice = 0

    def _begin_end(self):
        """Start camera return zoom; clear text."""
        self._returning = True
        self._zoom_progress = 0.0
        self._current_text = ""
        self._choices = None

    def _finish(self):
        """Fully end dialogue after camera returns."""
        self.active = False
        self._returning = False
        self._target = None
        self._play_cam = None
        self._lines = []
        self._nodes_dict = None
        self._current_node_id = None
        self.talk_sounds = []
        self._talk_sound_idx = 0

    @staticmethod
    def _world_to_screen(world_pos, camera, win_size):
        aspect = win_size[0] / win_size[1]
        view = camera.view_matrix()
        proj = camera.projection_matrix(aspect)
        clip = proj * view * glm.vec4(world_pos, 1.0)
        if clip.w <= 0:
            return None
        ndc = glm.vec3(clip) / clip.w
        sx = int((ndc.x * 0.5 + 0.5) * win_size[0])
        sy = int((1.0 - (ndc.y * 0.5 + 0.5)) * win_size[1])
        return (sx, sy)

    @staticmethod
    def _smoothstep(t):
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _word_wrap(text, font, max_width):
        words = text.split()
        if not words:
            return [""]
        lines = []
        current = words[0]
        for word in words[1:]:
            test = current + " " + word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines
