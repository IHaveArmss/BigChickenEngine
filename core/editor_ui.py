"""Editor UI — sidebar panel with spawn buttons, properties, settings, and save-as."""

import pygame


# ── Color Palette ──────────────────────────────────────────────────────
BG_COLOR = (20, 20, 30, 230)
PANEL_BORDER = (0, 200, 120, 200)
SECTION_COLOR = (0, 200, 120, 255)
LABEL_COLOR = (180, 180, 180, 255)
VALUE_COLOR = (255, 255, 255, 255)
BUTTON_BG = (40, 40, 60, 255)
BUTTON_HOVER = (60, 60, 90, 255)
BUTTON_ACTIVE = (30, 120, 60, 255)
BUTTON_TEXT = (220, 220, 220, 255)
INPUT_BG = (30, 30, 45, 255)
INPUT_BORDER = (80, 80, 120, 255)
INPUT_ACTIVE_BORDER = (0, 200, 120, 255)
INPUT_TEXT = (255, 255, 255, 255)
TOGGLE_ON = (0, 200, 120)
TOGGLE_OFF = (80, 80, 100)

PANEL_WIDTH = 300
PANEL_PADDING = 12
ROW_HEIGHT = 28
BUTTON_HEIGHT = 32
INPUT_HEIGHT = 26


class TextInput:
    """A clickable text input field."""

    def __init__(self, x, y, w, h, label, value="", on_change=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.text = str(value)
        self.active = False
        self.on_change = on_change
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            if self.active:
                self.cursor_timer = 0
                self.cursor_visible = True
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN or event.key == pygame.K_TAB:
                self.active = False
                if self.on_change:
                    self.on_change(self.text)
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                if self.on_change:
                    self.on_change(self.text)
            elif event.key == pygame.K_ESCAPE:
                self.active = False
            else:
                if event.unicode and event.unicode.isprintable():
                    self.text += event.unicode
                    if self.on_change:
                        self.on_change(self.text)

    def update(self, dt):
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer > 0.5:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0

    def draw(self, surface, font):
        border_color = INPUT_ACTIVE_BORDER if self.active else INPUT_BORDER
        pygame.draw.rect(surface, INPUT_BG, self.rect)
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=3)

        text_surf = font.render(self.text, True, INPUT_TEXT[:3])
        text_x = self.rect.x + 6
        text_y = self.rect.y + (self.rect.h - text_surf.get_height()) // 2
        clip = pygame.Rect(self.rect.x + 4, self.rect.y, self.rect.w - 8, self.rect.h)
        surface.set_clip(clip)
        surface.blit(text_surf, (text_x, text_y))
        surface.set_clip(None)

        if self.active and self.cursor_visible:
            cursor_x = text_x + text_surf.get_width() + 1
            if cursor_x < self.rect.right - 4:
                pygame.draw.line(surface, INPUT_TEXT[:3],
                                 (cursor_x, self.rect.y + 4),
                                 (cursor_x, self.rect.bottom - 4), 1)


class Button:
    """A clickable UI button."""

    def __init__(self, x, y, w, h, text, icon_color=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.icon_color = icon_color
        self.hovered = False

    def check_hover(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        return self.hovered

    def check_click(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

    def draw(self, surface, font, active=False):
        if active:
            color = BUTTON_ACTIVE
        elif self.hovered:
            color = BUTTON_HOVER
        else:
            color = BUTTON_BG
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        border = (0, 255, 120) if active else PANEL_BORDER[:3]
        pygame.draw.rect(surface, border, self.rect, 1, border_radius=4)

        tx = self.rect.x + 10
        if self.icon_color:
            icon_rect = pygame.Rect(self.rect.x + 8, self.rect.y + 8, 16, 16)
            pygame.draw.rect(surface, self.icon_color, icon_rect, border_radius=2)
            tx = self.rect.x + 32

        text_surf = font.render(self.text, True, BUTTON_TEXT[:3])
        text_y = self.rect.y + (self.rect.h - text_surf.get_height()) // 2
        surface.blit(text_surf, (tx, text_y))


class EditorUI:
    """Full editor sidebar with spawn, properties, settings, and save-as."""

    def __init__(self, win_size):
        self.win_size = win_size
        self.visible = False

        pygame.font.init()
        self.font = pygame.font.SysFont('Consolas', 14)
        self.font_bold = pygame.font.SysFont('Consolas', 14, bold=True)
        self.font_section = pygame.font.SysFont('Consolas', 16, bold=True)

        # Panel position (right side)
        self.panel_x = win_size[0] - PANEL_WIDTH - 10
        self.panel_y = 10

        bx = self.panel_x + PANEL_PADDING
        bw = PANEL_WIDTH - PANEL_PADDING * 2

        # Spawn buttons (positions will be set during draw)
        self.spawn_buttons = {
            'cube': Button(bx, 0, bw, BUTTON_HEIGHT, "  Cube", (100, 100, 255)),
            'triangle': Button(bx, 0, bw, BUTTON_HEIGHT, "  Triangle", (255, 100, 50)),
            'light': Button(bx, 0, bw, BUTTON_HEIGHT, "  Point Light", (255, 230, 100)),
        }

        # Placement mode: when user clicks a spawn button, the next viewport
        # click will place the object where the ray hits the floor
        self.placement_mode = None  # None or 'cube'/'triangle'/'light'

        # Property inputs (built dynamically)
        self.prop_inputs = {}
        self._current_obj_name = None

        # Save As field
        self.save_as_input = TextInput(bx, 0, bw - 60, INPUT_HEIGHT, 'filename', 'my_level')
        self.save_as_button = Button(bx + bw - 54, 0, 54, INPUT_HEIGHT, "Save")

        # Autosave toggle
        self.autosave_enabled = False
        self.autosave_toggle_rect = pygame.Rect(0, 0, 40, 22)

    def _build_property_inputs(self, obj):
        if obj is None:
            self.prop_inputs = {}
            self._current_obj_name = None
            return

        name = obj.name
        if name == self._current_obj_name:
            return

        self._current_obj_name = name
        self.prop_inputs = {}

        pos = obj.position
        scl = obj.scale
        color = getattr(obj.meshes[0], 'color', None) if obj.meshes else None

        self.prop_inputs = {
            'pos_x': {'label': 'X', 'value': f'{pos.x:.2f}', 'field': None},
            'pos_y': {'label': 'Y', 'value': f'{pos.y:.2f}', 'field': None},
            'pos_z': {'label': 'Z', 'value': f'{pos.z:.2f}', 'field': None},
            'scl_x': {'label': 'X', 'value': f'{scl.x:.3f}', 'field': None},
            'scl_y': {'label': 'Y', 'value': f'{scl.y:.3f}', 'field': None},
            'scl_z': {'label': 'Z', 'value': f'{scl.z:.3f}', 'field': None},
            'alpha': {'label': 'Alpha', 'value': f'{getattr(obj, "alpha", 1.0):.2f}', 'field': None},
        }

        if color is not None:
            r = int(min(1, max(0, color.x)) * 255)
            g = int(min(1, max(0, color.y)) * 255)
            b = int(min(1, max(0, color.z)) * 255)
            hex_str = f'#{r:02X}{g:02X}{b:02X}'
            self.prop_inputs['color'] = {'label': 'Color', 'value': hex_str, 'field': None}

        if obj.is_light:
            self.prop_inputs['intensity'] = {
                'label': 'Intensity',
                'value': f'{obj.light_intensity:.2f}',
                'field': None,
            }

        self.prop_inputs['folder'] = {
            'label': 'Folder',
            'value': getattr(obj, 'folder', 'Scene'),
            'field': None,
        }

    def handle_event(self, event, mouse_pos):
        """Handle events. Returns action dict or None."""
        if not self.visible:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Spawn buttons → enter placement mode
            for spawn_type, btn in self.spawn_buttons.items():
                if btn.check_click(mouse_pos):
                    if self.placement_mode == spawn_type:
                        # Toggle off
                        self.placement_mode = None
                    else:
                        self.placement_mode = spawn_type
                    return None  # consumed

            # Save As button
            if self.save_as_button.check_click(mouse_pos):
                return {'action': 'save_as', 'filename': self.save_as_input.text}

            # Autosave toggle
            if self.autosave_toggle_rect.collidepoint(mouse_pos):
                self.autosave_enabled = not self.autosave_enabled
                return {'action': 'autosave_toggle', 'enabled': self.autosave_enabled}

        # Forward to text inputs
        self.save_as_input.handle_event(event)
        for key, info in self.prop_inputs.items():
            if info['field']:
                info['field'].handle_event(event)

        return None

    def update(self, dt, mouse_pos, selected_obj=None):
        if not self.visible:
            return

        for btn in self.spawn_buttons.values():
            btn.check_hover(mouse_pos)
        self.save_as_button.check_hover(mouse_pos)

        self._build_property_inputs(selected_obj)

        self.save_as_input.update(dt)
        for key, info in self.prop_inputs.items():
            if info['field']:
                info['field'].update(dt)

    def read_property_values(self):
        values = {}
        for key, info in self.prop_inputs.items():
            if info['field']:
                values[key] = info['field'].text
        return values

    def refresh_values(self, obj):
        if obj is None:
            return
        pos = obj.position
        scl = obj.scale
        field_map = {
            'pos_x': f'{pos.x:.2f}', 'pos_y': f'{pos.y:.2f}', 'pos_z': f'{pos.z:.2f}',
            'scl_x': f'{scl.x:.3f}', 'scl_y': f'{scl.y:.3f}', 'scl_z': f'{scl.z:.3f}',
        }
        for key, val in field_map.items():
            if key in self.prop_inputs:
                info = self.prop_inputs[key]
                if info['field'] and not info['field'].active:
                    info['field'].text = val

    def is_point_on_panel(self, pos):
        if not self.visible:
            return False
        panel_rect = pygame.Rect(self.panel_x, self.panel_y,
                                 PANEL_WIDTH, self.win_size[1] - 20)
        return panel_rect.collidepoint(pos)

    def has_active_input(self):
        if self.save_as_input.active:
            return True
        for key, info in self.prop_inputs.items():
            if info['field'] and info['field'].active:
                return True
        return False

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface):
        if not self.visible:
            return

        panel_h = self.win_size[1] - 20
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, PANEL_WIDTH, panel_h)
        bg = pygame.Surface((PANEL_WIDTH, panel_h), pygame.SRCALPHA)
        bg.fill(BG_COLOR)
        surface.blit(bg, (self.panel_x, self.panel_y))
        pygame.draw.rect(surface, PANEL_BORDER, panel_rect, 2, border_radius=6)

        y = self.panel_y + PANEL_PADDING
        bx = self.panel_x + PANEL_PADDING
        bw = PANEL_WIDTH - PANEL_PADDING * 2

        # ── Title ──
        title_surf = self.font_section.render("EDITOR", True, SECTION_COLOR[:3])
        surface.blit(title_surf, (bx, y))
        y += 28

        # ── Spawn (click to place) ──
        section_surf = self.font_bold.render("── Spawn (click to place) ──", True, (100, 200, 255))
        surface.blit(section_surf, (bx, y))
        y += 22

        for spawn_type, btn in self.spawn_buttons.items():
            btn.rect.y = y
            is_active = (self.placement_mode == spawn_type)
            btn.draw(surface, self.font, active=is_active)
            y += BUTTON_HEIGHT + 6

        # Placement hint
        if self.placement_mode:
            hint = self.font.render(
                f"Click viewport to place {self.placement_mode}",
                True, (0, 255, 120)
            )
            surface.blit(hint, (bx, y))
            y += 18
        y += 6

        # ── Properties ──
        if self._current_obj_name and self.prop_inputs:
            section_surf = self.font_bold.render(
                f"── {self._current_obj_name} ──", True, (100, 200, 255)
            )
            surface.blit(section_surf, (bx, y))
            y += 24

            y = self._draw_properties(surface, y, bx, bw)
            y += 6
        else:
            hint = self.font.render("Select object to edit", True, (120, 120, 120))
            surface.blit(hint, (bx, y))
            y += 20

        # ── Settings ──
        y += 4
        section_surf = self.font_bold.render("── Settings ──", True, (100, 200, 255))
        surface.blit(section_surf, (bx, y))
        y += 24

        # Autosave toggle
        label = self.font.render("Autosave (30s)", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 2))

        toggle_x = bx + bw - 44
        self.autosave_toggle_rect = pygame.Rect(toggle_x, y, 40, 22)
        # Draw toggle switch
        bg_c = TOGGLE_ON if self.autosave_enabled else TOGGLE_OFF
        pygame.draw.rect(surface, bg_c, self.autosave_toggle_rect, border_radius=11)
        knob_x = toggle_x + 20 if self.autosave_enabled else toggle_x + 2
        pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 11), 8)
        y += 30

        # ── Save As ──
        section_surf = self.font_bold.render("── Save As ──", True, (100, 200, 255))
        surface.blit(section_surf, (bx, y))
        y += 22

        hint = self.font.render("scenes/", True, (120, 120, 120))
        surface.blit(hint, (bx, y + 4))
        prefix_w = hint.get_width()

        input_w = bw - prefix_w - 60
        self.save_as_input.rect = pygame.Rect(bx + prefix_w + 4, y, input_w, INPUT_HEIGHT)
        self.save_as_input.draw(surface, self.font)

        suffix = self.font.render(".json", True, (120, 120, 120))
        surface.blit(suffix, (bx + prefix_w + input_w + 6, y + 4))

        self.save_as_button.rect = pygame.Rect(bx + bw - 50, y + INPUT_HEIGHT + 6, 50, INPUT_HEIGHT)
        self.save_as_button.draw(surface, self.font)
        y += INPUT_HEIGHT + 36

    def _draw_properties(self, surface, y, bx, bw):
        """Draw position, scale, and color fields. Returns new y."""
        fw = bw - 10
        single_w = fw // 3 - 12

        # Position
        label_surf = self.font_bold.render("Position", True, LABEL_COLOR[:3])
        surface.blit(label_surf, (bx, y))
        y += 18

        x = bx
        for key in ['pos_x', 'pos_y', 'pos_z']:
            if key in self.prop_inputs:
                info = self.prop_inputs[key]
                lbl_c = {'pos_x': (255, 80, 80), 'pos_y': (80, 255, 80), 'pos_z': (80, 80, 255)}
                lbl = self.font_bold.render(info['label'], True, lbl_c[key])
                surface.blit(lbl, (x, y + 3))
                if info['field'] is None:
                    info['field'] = TextInput(x + 16, y, single_w, INPUT_HEIGHT,
                                              info['label'], info['value'])
                info['field'].rect = pygame.Rect(x + 16, y, single_w, INPUT_HEIGHT)
                info['field'].draw(surface, self.font)
                x += single_w + 24
        y += INPUT_HEIGHT + 10

        # Scale
        label_surf = self.font_bold.render("Scale", True, LABEL_COLOR[:3])
        surface.blit(label_surf, (bx, y))
        y += 18

        x = bx
        for key in ['scl_x', 'scl_y', 'scl_z']:
            if key in self.prop_inputs:
                info = self.prop_inputs[key]
                lbl_c = {'scl_x': (255, 80, 80), 'scl_y': (80, 255, 80), 'scl_z': (80, 80, 255)}
                lbl = self.font_bold.render(info['label'], True, lbl_c[key])
                surface.blit(lbl, (x, y + 3))
                if info['field'] is None:
                    info['field'] = TextInput(x + 16, y, single_w, INPUT_HEIGHT,
                                              info['label'], info['value'])
                info['field'].rect = pygame.Rect(x + 16, y, single_w, INPUT_HEIGHT)
                info['field'].draw(surface, self.font)
                x += single_w + 24
        y += INPUT_HEIGHT + 10

        # Color (hex)
        if 'color' in self.prop_inputs:
            info = self.prop_inputs['color']
            label_surf = self.font_bold.render("Color (hex)", True, LABEL_COLOR[:3])
            surface.blit(label_surf, (bx, y))
            y += 18

            full_w = PANEL_WIDTH - PANEL_PADDING * 2 - 50
            if info['field'] is None:
                info['field'] = TextInput(bx, y, full_w, INPUT_HEIGHT,
                                          'Color', info['value'])
            info['field'].rect = pygame.Rect(bx, y, full_w, INPUT_HEIGHT)
            info['field'].draw(surface, self.font)

            hex_val = info['field'].text
            rgb = self._parse_hex(hex_val)
            if rgb:
                swatch_rect = pygame.Rect(bx + full_w + 6, y, 30, INPUT_HEIGHT)
                pygame.draw.rect(surface, rgb, swatch_rect, border_radius=3)
                pygame.draw.rect(surface, (200, 200, 200), swatch_rect, 1, border_radius=3)
            y += INPUT_HEIGHT + 10

        # Intensity (lights only)
        if 'intensity' in self.prop_inputs:
            info = self.prop_inputs['intensity']
            label_surf = self.font_bold.render("Intensity", True, (255, 230, 100))
            surface.blit(label_surf, (bx, y))
            y += 18

            full_w = PANEL_WIDTH - PANEL_PADDING * 2 - 10
            if info['field'] is None:
                info['field'] = TextInput(bx, y, full_w, INPUT_HEIGHT,
                                          'Intensity', info['value'])
            info['field'].rect = pygame.Rect(bx, y, full_w, INPUT_HEIGHT)
            info['field'].draw(surface, self.font)
            y += INPUT_HEIGHT + 10

        # Alpha (all objects)
        if 'alpha' in self.prop_inputs:
            info = self.prop_inputs['alpha']
            label_surf = self.font_bold.render("Opacity (0-1)", True, LABEL_COLOR[:3])
            surface.blit(label_surf, (bx, y))
            y += 18

            full_w = PANEL_WIDTH - PANEL_PADDING * 2 - 10
            if info['field'] is None:
                info['field'] = TextInput(bx, y, full_w, INPUT_HEIGHT,
                                          'Alpha', info['value'])
            info['field'].rect = pygame.Rect(bx, y, full_w, INPUT_HEIGHT)
            info['field'].draw(surface, self.font)
            y += INPUT_HEIGHT + 10

        # Folder
        if 'folder' in self.prop_inputs:
            info = self.prop_inputs['folder']
            label_surf = self.font_bold.render("Folder", True, (255, 200, 80))
            surface.blit(label_surf, (bx, y))
            y += 18

            full_w = PANEL_WIDTH - PANEL_PADDING * 2 - 10
            if info['field'] is None:
                info['field'] = TextInput(bx, y, full_w, INPUT_HEIGHT,
                                          'Folder', info['value'])
            info['field'].rect = pygame.Rect(bx, y, full_w, INPUT_HEIGHT)
            info['field'].draw(surface, self.font)
            y += INPUT_HEIGHT + 10

        return y

    @staticmethod
    def _parse_hex(hex_str):
        h = hex_str.strip().lstrip('#')
        if len(h) == 6:
            try:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except ValueError:
                pass
        elif len(h) == 3:
            try:
                return (int(h[0]*2, 16), int(h[1]*2, 16), int(h[2]*2, 16))
            except ValueError:
                pass
        return None
