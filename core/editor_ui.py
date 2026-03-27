"""Editor UI — sidebar panel with spawn buttons, properties, settings, and save-as."""

import os
import pygame
from core.utils import normalize_script_names


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
DROPDOWN_BG = (35, 35, 50)
DROPDOWN_HOVER = (55, 55, 80)
DROPDOWN_BORDER = (90, 90, 130)

PANEL_WIDTH = 340


class CollapsibleSection:
    """A collapsible section header that can be clicked to expand/collapse."""
    
    def __init__(self, title, default_expanded=True):
        self.title = title
        self.expanded = default_expanded
        self.rect = pygame.Rect(0, 0, 0, 0)
        self._collapsed_height = 24
        self._expanded_height = 24
    
    @property
    def height(self):
        return self._collapsed_height if not self.expanded else 0
    
    def get_content_height(self):
        return 0
    
    def toggle(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.expanded = not self.expanded
            return True
        return False
    
    def draw(self, surface, font, bx, y):
        self.rect = pygame.Rect(bx, y, PANEL_WIDTH - PANEL_PADDING * 2, self._collapsed_height)
        
        bg = pygame.Surface((self.rect.width, self._collapsed_height), pygame.SRCALPHA)
        bg.fill((30, 30, 45, 200))
        surface.blit(bg, (bx, y))
        
        arrow = "▼" if self.expanded else "▶"
        arrow_surf = font.render(arrow, True, SECTION_COLOR[:3])
        surface.blit(arrow_surf, (bx + 4, y + 4))
        
        title_surf = font.render(self.title, True, SECTION_COLOR[:3])
        surface.blit(title_surf, (bx + 22, y + 4))
        
        pygame.draw.rect(surface, SECTION_COLOR[:3], self.rect, 1, border_radius=3)
        
        return y + self._collapsed_height


class DropdownSelect:
    """A simple dropdown selector for model/file selection."""
    
    def __init__(self, x, y, width, items, default_index=0):
        self.rect = pygame.Rect(x, y, width, 26)
        self.items = list(items)
        self.selected_index = default_index if default_index < len(items) else 0
        self.open = False
        self.option_rects = []
    
    @property
    def selected(self):
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return ""
    
    def set_items(self, items):
        self.items = list(items)
        if self.selected_index >= len(items):
            self.selected_index = 0
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
                return True
            elif self.open:
                for i, opt_rect in enumerate(self.option_rects):
                    if opt_rect.collidepoint(event.pos):
                        self.selected_index = i
                        self.open = False
                        return True
                self.open = False
        return False
    
    def draw(self, surface, font, bx, y):
        self.rect.y = y
        
        bg_color = DROPDOWN_BG
        border_color = DROPDOWN_BORDER
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)
        pygame.draw.rect(surface, border_color, self.rect, 1, border_radius=4)
        
        selected_text = self.items[self.selected_index] if self.items else "(none)"
        text_surf = font.render(selected_text[:30], True, (220, 220, 220))
        surface.blit(text_surf, (self.rect.x + 8, self.rect.y + 5))
        
        arrow = "▼" if self.open else "▲"
        arrow_surf = font.render(arrow, True, (150, 150, 180))
        surface.blit(arrow_surf, (self.rect.right - 18, self.rect.y + 5))
        
        self.option_rects = []
        if self.open and self.items:
            for i, item in enumerate(self.items):
                opt_rect = pygame.Rect(self.rect.x, self.rect.y + 26 + i * 24, self.rect.width, 24)
                self.option_rects.append(opt_rect)
                
                hover = opt_rect.collidepoint(pygame.mouse.get_pos())
                opt_bg = DROPDOWN_HOVER if hover else DROPDOWN_BG
                pygame.draw.rect(surface, opt_bg, opt_rect)
                pygame.draw.rect(surface, DROPDOWN_BORDER, opt_rect, 1)
                
                opt_text = font.render(item[:30], True, (220, 220, 220))
                surface.blit(opt_text, (opt_rect.x + 8, opt_rect.y + 4))
        
        if self.open and self.items:
            return y + 32 + (len(self.items) * 24)
        return y + 32
PANEL_PADDING = 12
ROW_HEIGHT = 28
BUTTON_HEIGHT = 32
INPUT_HEIGHT = 26
SCROLL_STEP = 26


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

        # Model selection for spawning imported models
        self.available_models = []
        self.model_dropdown = DropdownSelect(bx, 0, bw, ["(select model)"])
        self.model_path_input = TextInput(bx, 0, bw - 70, INPUT_HEIGHT, 'path', 'models/')
        self.model_spawn_btn = Button(bx + bw - 64, 0, 64, INPUT_HEIGHT, "Spawn")
        self.model_refresh_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Refresh")

        # Placement mode: when user clicks a spawn button, the next viewport
        # click will place the object where the ray hits the floor
        self.placement_mode = None  # None or 'cube'/'triangle'/'light'/'model'
        self._pending_model_path = None  # Stores model path when spawning models

        # Property inputs (built dynamically)
        self.prop_inputs = {}
        self._current_obj_name = None
        self._script_confirmation = None
        self.scroll_y = 0
        self.max_scroll = 0

        # Save As field
        self.save_as_input = TextInput(bx, 0, bw - 60, INPUT_HEIGHT, 'filename', 'my_level')
        self.save_as_button = Button(bx + bw - 54, 0, 54, INPUT_HEIGHT, "Save")
        self.save_current_button = Button(bx, 0, bw, INPUT_HEIGHT, "Save Current Scene")
        self.undo_button = Button(bx, 0, 0, INPUT_HEIGHT, "Undo")
        self.redo_button = Button(bx, 0, 0, INPUT_HEIGHT, "Redo")

        # Autosave toggle
        self.autosave_enabled = False
        self.autosave_toggle_rect = pygame.Rect(0, 0, 40, 22)
        # Retro/PS2 render settings (UI-owned; engine reads/applies)
        self.ps2_enabled = True
        self.ps2_toggle_rect = pygame.Rect(0, 0, 40, 22)
        self.postprocess_enabled = True
        self.postprocess_toggle_rect = pygame.Rect(0, 0, 40, 22)
        self.pixel_size_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'Pixel', '3')
        self.quantize_enabled = True
        self.quantize_toggle_rect = pygame.Rect(0, 0, 40, 22)
        self.quantize_steps_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'QSteps', '32')
        self.dither_enabled = False
        self.dither_toggle_rect = pygame.Rect(0, 0, 40, 22)

        self.lighting_ramp_enabled = True
        self.lighting_ramp_toggle_rect = pygame.Rect(0, 0, 40, 22)
        self.lighting_ramp_steps_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'Ramp', '4')
        self.specular_banding_enabled = False
        self.specular_toggle_rect = pygame.Rect(0, 0, 40, 22)
        self.specular_steps_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'SSteps', '3')

        self.wobble_enabled = False
        self.wobble_toggle_rect = pygame.Rect(0, 0, 40, 22)
        self.wobble_pixel_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'WobPx', '2')
        self.directional_shadows_enabled = True
        self.directional_shadows_toggle_rect = pygame.Rect(0, 0, 40, 22)
        self.directional_shadow_resolution_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'ShRes', '1024')
        self.directional_shadow_distance_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'ShDist', '40.0')
        self.shadow_bias_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'ShBias', '0.0015')
        self.spot_shadows_enabled = True
        self.spot_shadows_toggle_rect = pygame.Rect(0, 0, 40, 22)
        self.spot_shadow_resolution_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'SpRes', '512')
        self.ambient_strength_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'Amb', '0.15')
        self.ambient_color_input = TextInput(bx, 0, 80, INPUT_HEIGHT, 'AmbColor', '#FFFFFF')
        self.sun_azimuth_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'SunAz', '45')
        self.sun_elevation_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'SunEl', '-55')
        self.sun_intensity_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'SunInt', '1.0')
        
        self.global_gravity_input = TextInput(bx, 0, bw, INPUT_HEIGHT, 'Gravity', '-9.81')
        self.scene_load_input = TextInput(bx, 0, bw, INPUT_HEIGHT, 'Scene', 'floor')
        self.scene_load_button = Button(bx, 0, 0, INPUT_HEIGHT, "Load")
        self.scene_reload_button = Button(bx, 0, 0, INPUT_HEIGHT, "Reload")
        self.current_scene_file = ''
        self.available_scenes = []
        self.scene_quick_rects = []
        self.prefab_name_input = TextInput(bx, 0, bw, INPUT_HEIGHT, 'Prefab', 'new_prefab')
        self.prefab_save_button = Button(bx, 0, 0, INPUT_HEIGHT, "Save Selected")
        self.prefab_spawn_button = Button(bx, 0, 0, INPUT_HEIGHT, "Spawn")
        self.available_prefabs = []
        self.prefab_quick_rects = []

        # Collapsible settings sections
        self.section_settings = CollapsibleSection("── Settings ──", default_expanded=True)
        self.section_ps2 = CollapsibleSection("── PS2 Graphics ──", default_expanded=False)
        self.section_sun = CollapsibleSection("── Sun & Ambient ──", default_expanded=False)
        self.section_shadows = CollapsibleSection("── Shadows ──", default_expanded=False)

        # Animation Recording
        self.recording_name_input = TextInput(bx, 0, bw - 60, INPUT_HEIGHT, 'anim_name', 'new_clip')
        self.record_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Rec")
        self.play_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Play")
        self.stop_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Stop")
        self.clear_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Clear")
        self.save_anim_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Save")
        
        self.is_recording = False
        self.recorded_keyframes = [] # list of {time, pos, rot, scl}
        self.anim_smooth = True
        self.anim_interval = TextInput(bx, 0, 60, INPUT_HEIGHT, 'interval', '0.5')

        self.section_cutscene = CollapsibleSection("── Cutscene Maker ──", default_expanded=False)
        self.cutscene_name_input = TextInput(bx, 0, bw - 60, INPUT_HEIGHT, 'name', 'new_cutscene')
        self.cutscene_speed_input = TextInput(bx, 0, 60, INPUT_HEIGHT, 'speed', '1.0')
        self.cutscene_add_point_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Add Point")
        self.cutscene_clear_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Clear")
        self.cutscene_play_btn = Button(bx, 0, 50, INPUT_HEIGHT, "Play")
        self.cutscene_stop_btn = Button(bx, 0, 50, INPUT_HEIGHT, "Stop")
        self.cutscene_save_btn = Button(bx, 0, 50, INPUT_HEIGHT, "Save")
        self.cutscene_load_btn = Button(bx, 0, 50, INPUT_HEIGHT, "Load")
        self.cutscene_can_player_move = True
        self.cutscene_can_player_move_rect = pygame.Rect(0, 0, 40, 22)
        self.cutscene_is_looping = False
        self.cutscene_loop_rect = pygame.Rect(0, 0, 40, 22)
        self.cutscene_dropdown = DropdownSelect(bx, 0, bw, [])
        self.cutscene_waypoint_count = 0
        self.available_cutscenes = []

        self.section_sprite = CollapsibleSection("── Sprite Spawner ──", default_expanded=False)
        self.sprite_path_input = TextInput(bx, 0, bw, INPUT_HEIGHT, 'path', 'assets/sprites/')
        self.sprite_name_input = TextInput(bx, 0, bw, INPUT_HEIGHT, 'name', 'sprite')
        self.sprite_spawn_btn = Button(bx, 0, 70, INPUT_HEIGHT, "Spawn")
        self.sprite_billboard = True
        self.sprite_billboard_rect = pygame.Rect(0, 0, 40, 22)
        self.sprite_autocrop = True
        self.sprite_autocrop_rect = pygame.Rect(0, 0, 40, 22)

    def update_gravity_ui(self, gravity):
        if not self.global_gravity_input.active:
            self.global_gravity_input.text = f"{gravity:.2f}"

    def refresh_models(self, base_path="models"):
        """Scan for available model files (.obj, .glb, .gltf)."""
        self.available_models = []
        if os.path.isdir(base_path):
            for f in os.listdir(base_path):
                if f.lower().endswith(('.obj', '.glb', '.gltf')):
                    self.available_models.append(f)
        self.available_models.sort()
        if self.available_models:
            self.model_dropdown.set_items(self.available_models)
        else:
            self.model_dropdown.set_items(["(no models found)"])

    def _draw_labeled_input(self, surface, label, input_field, y):
        bx = self.panel_x + PANEL_PADDING
        bw = PANEL_WIDTH - PANEL_PADDING * 2
        label_s = self.font.render(label, True, LABEL_COLOR[:3])
        surface.blit(label_s, (bx, y + 4))
        input_field.rect = pygame.Rect(bx + 90, y, bw - 90, INPUT_HEIGHT)
        input_field.draw(surface, self.font)
        return y + INPUT_HEIGHT + 4

    def _draw_ps2_section(self, surface, bx, bw, y):
        y = self.section_ps2.draw(surface, self.font_bold, bx, y)
        if not self.section_ps2.expanded:
            return y
        
        def draw_toggle_row(label_text, enabled, rect_attr):
            nonlocal y
            label_s = self.font.render(label_text, True, LABEL_COLOR[:3])
            surface.blit(label_s, (bx, y + 2))
            toggle_x = bx + bw - 44
            rect = pygame.Rect(toggle_x, y, 40, 22)
            setattr(self, rect_attr, rect)
            bg_c = TOGGLE_ON if enabled else TOGGLE_OFF
            pygame.draw.rect(surface, bg_c, rect, border_radius=11)
            knob_x = toggle_x + 20 if enabled else toggle_x + 2
            pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 11), 8)
            y += 28

        draw_toggle_row("PS2 Style", self.ps2_enabled, "ps2_toggle_rect")
        draw_toggle_row("Postprocess", self.postprocess_enabled, "postprocess_toggle_rect")

        label = self.font.render("Pixel Size", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.pixel_size_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.pixel_size_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        draw_toggle_row("Quantize", self.quantize_enabled, "quantize_toggle_rect")
        label = self.font.render("Quant Steps", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.quantize_steps_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.quantize_steps_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        draw_toggle_row("Dither", self.dither_enabled, "dither_toggle_rect")
        draw_toggle_row("Light Ramp", self.lighting_ramp_enabled, "lighting_ramp_toggle_rect")
        
        label = self.font.render("Ramp Steps", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.lighting_ramp_steps_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.lighting_ramp_steps_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        draw_toggle_row("Spec Band", self.specular_banding_enabled, "specular_toggle_rect")
        label = self.font.render("Spec Steps", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.specular_steps_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.specular_steps_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        draw_toggle_row("PS1 Wobble", self.wobble_enabled, "wobble_toggle_rect")
        label = self.font.render("Wobble Px", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.wobble_pixel_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.wobble_pixel_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 10
        return y

    def _draw_sun_section(self, surface, bx, bw, y):
        y = self.section_sun.draw(surface, self.font_bold, bx, y)
        if not self.section_sun.expanded:
            return y
        
        label = self.font.render("Ambient Intensity", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        amb_w = 60
        color_w = 96
        self.ambient_strength_input.rect = pygame.Rect(bx + bw - (amb_w + color_w + 10), y, amb_w, INPUT_HEIGHT)
        self.ambient_strength_input.draw(surface, self.font)
        self.ambient_color_input.rect = pygame.Rect(bx + bw - color_w, y, color_w, INPUT_HEIGHT)
        self.ambient_color_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6
        
        label = self.font.render("Sun Azimuth / Elev.", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        sun_w = 60
        self.sun_azimuth_input.rect = pygame.Rect(bx + bw - (sun_w * 2 + 6), y, sun_w, INPUT_HEIGHT)
        self.sun_azimuth_input.draw(surface, self.font)
        self.sun_elevation_input.rect = pygame.Rect(bx + bw - sun_w, y, sun_w, INPUT_HEIGHT)
        self.sun_elevation_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6
        
        label = self.font.render("Sun Intensity", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.sun_intensity_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.sun_intensity_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 4
        
        hint = self.font.render("Az: around Y (0=+X, 90=+Z)  El: up/down", True, (140, 140, 150))
        surface.blit(hint, (bx, y))
        y += 18
        return y

    def _draw_shadows_section(self, surface, bx, bw, y):
        y = self.section_shadows.draw(surface, self.font_bold, bx, y)
        if not self.section_shadows.expanded:
            return y
        
        def draw_toggle_row(label_text, enabled, rect_attr):
            nonlocal y
            label_s = self.font.render(label_text, True, LABEL_COLOR[:3])
            surface.blit(label_s, (bx, y + 2))
            toggle_x = bx + bw - 44
            rect = pygame.Rect(toggle_x, y, 40, 22)
            setattr(self, rect_attr, rect)
            bg_c = TOGGLE_ON if enabled else TOGGLE_OFF
            pygame.draw.rect(surface, bg_c, rect, border_radius=11)
            knob_x = toggle_x + 20 if enabled else toggle_x + 2
            pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 11), 8)
            y += 28

        draw_toggle_row("Directional Shadows", self.directional_shadows_enabled, "directional_shadows_toggle_rect")
        
        label = self.font.render("Dir Map Size", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.directional_shadow_resolution_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.directional_shadow_resolution_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6
        
        label = self.font.render("Dir Distance", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.directional_shadow_distance_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.directional_shadow_distance_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6
        
        label = self.font.render("Shadow Bias", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.shadow_bias_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.shadow_bias_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 8

        draw_toggle_row("Point Light Shadows", self.spot_shadows_enabled, "spot_shadows_toggle_rect")
        
        label = self.font.render("Spot Map Size", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.spot_shadow_resolution_input.rect = pygame.Rect(bx + bw - 80, y, 80, INPUT_HEIGHT)
        self.spot_shadow_resolution_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 10
        return y

    def _draw_cutscene_section(self, surface, bx, bw, y):
        label = self.font.render("Name", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.cutscene_name_input.rect = pygame.Rect(bx + 50, y, bw - 100, INPUT_HEIGHT)
        self.cutscene_name_input.draw(surface, self.font)
        self.cutscene_save_btn.rect = pygame.Rect(bx + bw - 45, y, 45, INPUT_HEIGHT)
        self.cutscene_save_btn.draw(surface, self.font)
        self.cutscene_load_btn.rect = pygame.Rect(bx + bw - 95, y, 45, INPUT_HEIGHT)
        self.cutscene_load_btn.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        label = self.font.render("Speed", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.cutscene_speed_input.rect = pygame.Rect(bx + 50, y, 60, INPUT_HEIGHT)
        self.cutscene_speed_input.draw(surface, self.font)
        label = self.font.render("Can Move", True, LABEL_COLOR[:3])
        surface.blit(label, (bx + 120, y + 4))
        self.cutscene_can_player_move_rect = pygame.Rect(bx + 185, y, 36, 18)
        bg_c = TOGGLE_ON if self.cutscene_can_player_move else TOGGLE_OFF
        pygame.draw.rect(surface, bg_c, self.cutscene_can_player_move_rect, border_radius=9)
        knob_x = bx + 185 + 18 if self.cutscene_can_player_move else bx + 185 + 2
        pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)
        label = self.font.render("Loop", True, LABEL_COLOR[:3])
        surface.blit(label, (bx + 230, y + 4))
        self.cutscene_loop_rect = pygame.Rect(bx + 265, y, 36, 18)
        bg_c = TOGGLE_ON if self.cutscene_is_looping else TOGGLE_OFF
        pygame.draw.rect(surface, bg_c, self.cutscene_loop_rect, border_radius=9)
        knob_x = bx + 265 + 18 if self.cutscene_is_looping else bx + 265 + 2
        pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)
        y += INPUT_HEIGHT + 6

        btn_w = 50
        spacing = 6
        self.cutscene_add_point_btn.rect = pygame.Rect(bx, y, btn_w, INPUT_HEIGHT)
        self.cutscene_play_btn.rect = pygame.Rect(bx + btn_w + spacing, y, btn_w, INPUT_HEIGHT)
        self.cutscene_stop_btn.rect = pygame.Rect(bx + (btn_w + spacing) * 2, y, btn_w, INPUT_HEIGHT)
        self.cutscene_clear_btn.rect = pygame.Rect(bx + (btn_w + spacing) * 3, y, btn_w, INPUT_HEIGHT)
        self.cutscene_add_point_btn.draw(surface, self.font)
        self.cutscene_play_btn.draw(surface, self.font)
        self.cutscene_stop_btn.draw(surface, self.font)
        self.cutscene_clear_btn.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        cutscene_files = self.available_cutscenes if hasattr(self, 'available_cutscenes') else []
        self.cutscene_dropdown.set_items(cutscene_files if cutscene_files else ["(no cutscenes)"])
        self.cutscene_dropdown.rect = pygame.Rect(bx, y, bw, 26)
        y = self.cutscene_dropdown.draw(surface, self.font, bx, y) - 4

        count_text = f"Waypoints: {self.cutscene_waypoint_count}"
        count_surf = self.font.render(count_text, True, (140, 140, 160))
        surface.blit(count_surf, (bx, y))
        y += 18
        return y

    def _draw_sprite_section(self, surface, bx, bw, y):

        label = self.font.render("Path:", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.sprite_path_input.rect = pygame.Rect(bx + 50, y, bw - 50, INPUT_HEIGHT)
        self.sprite_path_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        label = self.font.render("Name:", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 4))
        self.sprite_name_input.rect = pygame.Rect(bx + 50, y, bw - 50, INPUT_HEIGHT)
        self.sprite_name_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        self.sprite_spawn_btn.rect = pygame.Rect(bx, y, 70, INPUT_HEIGHT)
        self.sprite_spawn_btn.draw(surface, self.font)
        y += INPUT_HEIGHT + 10

        label = self.font.render("Billboard", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 2))
        self.sprite_billboard_rect = pygame.Rect(bx + 80, y, 36, 18)
        bg_c = TOGGLE_ON if self.sprite_billboard else TOGGLE_OFF
        pygame.draw.rect(surface, bg_c, self.sprite_billboard_rect, border_radius=9)
        knob_x = bx + 80 + 18 if self.sprite_billboard else bx + 80 + 2
        pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)

        label = self.font.render("Autocrop", True, LABEL_COLOR[:3])
        surface.blit(label, (bx + 130, y + 2))
        self.sprite_autocrop_rect = pygame.Rect(bx + 200, y, 36, 18)
        bg_c = TOGGLE_ON if self.sprite_autocrop else TOGGLE_OFF
        pygame.draw.rect(surface, bg_c, self.sprite_autocrop_rect, border_radius=9)
        knob_x = bx + 200 + 18 if self.sprite_autocrop else bx + 200 + 2
        pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)
        y += 28
        return y

    def set_scene_context(self, current_scene_file, available_scenes):
        self.current_scene_file = current_scene_file or ''
        self.available_scenes = list(available_scenes or [])
        if not self.scene_load_input.active and self.current_scene_file:
            base = os.path.basename(self.current_scene_file)
            if base.endswith('.json'):
                base = base[:-5]
            self.scene_load_input.text = base

    def set_prefab_context(self, prefab_names):
        self.available_prefabs = list(prefab_names or [])

    def _build_property_inputs(self, obj):
        if obj is None:
            self.prop_inputs = {}
            self._current_obj_name = None
            self._script_confirmation = None
            return

        name = obj.name
        if name == self._current_obj_name:
            return

        self._current_obj_name = name
        self._script_confirmation = None
        self.prop_inputs = {}

        pos = obj.position
        scl = obj.scale
        rot = obj.rotation_euler
        color = getattr(obj.meshes[0], 'color', None) if obj.meshes else None

        self.prop_inputs = {
            'pos_x': {'label': 'X', 'value': f'{pos.x:.2f}', 'field': None},
            'pos_y': {'label': 'Y', 'value': f'{pos.y:.2f}', 'field': None},
            'pos_z': {'label': 'Z', 'value': f'{pos.z:.2f}', 'field': None},
            'rot_x': {'label': 'X', 'value': f'{rot.x:.1f}', 'field': None},
            'rot_y': {'label': 'Y', 'value': f'{rot.y:.1f}', 'field': None},
            'rot_z': {'label': 'Z', 'value': f'{rot.z:.1f}', 'field': None},
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
            self.prop_inputs['light_casts_shadows'] = {
                'label': 'Light Shadow', 'value': getattr(obj, 'light_casts_shadows', True), 'field': 'toggle',
            }

        # --- Physics Properties ---
        self.prop_inputs['mass'] = {
            'label': 'Mass (kg)', 'value': f'{getattr(obj, "mass", 1.0):.2f}', 'field': None,
        }
        self.prop_inputs['bounciness'] = {
            'label': 'Bnciness', 'value': f'{getattr(obj, "bounciness", 0.0):.2f}', 'field': None,
        }
        self.prop_inputs['friction'] = {
            'label': 'Friction', 'value': f'{getattr(obj, "friction", 0.5):.2f}', 'field': None,
        }
        self.prop_inputs['drag'] = {
            'label': 'Drag', 'value': f'{getattr(obj, "drag", 0.02):.3f}', 'field': None,
        }
        # We handle booleans natively using toggles but we mock them in 'prop_inputs'
        self.prop_inputs['use_gravity'] = {
            'label': 'Use Grvy', 'value': getattr(obj, 'use_gravity', False), 'field': 'toggle',
        }
        self.prop_inputs['is_kinematic'] = {
            'label': 'Anchored', 'value': getattr(obj, 'is_kinematic', True), 'field': 'toggle',
        }
        self.prop_inputs['casts_shadows'] = {
            'label': 'Cast Shdw', 'value': getattr(obj, 'casts_shadows', True), 'field': 'toggle',
        }
        self.prop_inputs['receives_shadows'] = {
            'label': 'Recv Shdw', 'value': getattr(obj, 'receives_shadows', True), 'field': 'toggle',
        }
        self.prop_inputs['interactable'] = {
            'label': 'Interactable', 'value': getattr(obj, 'interactable', False), 'field': 'toggle',
        }
        self.prop_inputs['interaction_distance'] = {
            'label': 'Interact Dist', 'value': f'{getattr(obj, "interaction_distance", 3.0):.2f}', 'field': None,
        }

        self.prop_inputs['folder'] = {
            'label': 'Folder',
            'value': getattr(obj, 'folder', 'Scene'),
            'field': None,
        }
        
        attached_scripts = normalize_script_names(getattr(obj, 'scripts', []))
        self.prop_inputs['scripts'] = {
            'label': 'Scripts (names only)',
            'value': '',
            'attached': attached_scripts,
            'field': None,
        }

        if getattr(obj, 'animator', None) is not None:
            cfg = getattr(obj, 'anim_state_config', {})
            self.prop_inputs['use_anim_state_controller'] = {
                'label': 'Anim Ctrl',
                'value': bool(getattr(obj, 'use_anim_state_controller', False)),
                'field': 'toggle',
            }
            self.prop_inputs['anim_idle'] = {
                'label': 'Idle Clip', 'value': str(cfg.get('idle', 'idle')), 'field': None
            }
            self.prop_inputs['anim_run'] = {
                'label': 'Run Clip', 'value': str(cfg.get('run', 'run')), 'field': None
            }
            self.prop_inputs['anim_jump'] = {
                'label': 'Jump Clip', 'value': str(cfg.get('jump', 'jump')), 'field': None
            }
            self.prop_inputs['anim_fall'] = {
                'label': 'Fall Clip', 'value': str(cfg.get('fall', 'fall')), 'field': None
            }
            self.prop_inputs['anim_move_threshold'] = {
                'label': 'Move Thresh', 'value': f"{float(cfg.get('move_threshold', 0.1)):.3f}", 'field': None
            }
            self.prop_inputs['anim_vertical_threshold'] = {
                'label': 'Vert Thresh', 'value': f"{float(cfg.get('vertical_threshold', 0.15)):.3f}", 'field': None
            }
            
            self.prop_inputs['animation_clips'] = {
                'field': None,
                'clips': obj.animator.clip_names,
            }

    def handle_event(self, event, mouse_pos):
        """Handle events. Returns action dict or None."""
        if not self.visible:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
            self.scroll_y = max(0, self.scroll_y - SCROLL_STEP)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
            self.scroll_y = min(self.max_scroll, self.scroll_y + SCROLL_STEP)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.undo_button.check_click(mouse_pos):
                return {'action': 'undo'}
            if self.redo_button.check_click(mouse_pos):
                return {'action': 'redo'}
            if self.scene_load_button.check_click(mouse_pos):
                return {'action': 'load_scene', 'scene': self.scene_load_input.text}
            if self.scene_reload_button.check_click(mouse_pos):
                return {'action': 'reload_scene'}
            if self.save_current_button.check_click(mouse_pos):
                return {'action': 'save_current_scene'}
            if self.prefab_save_button.check_click(mouse_pos):
                return {'action': 'save_prefab_selected', 'prefab': self.prefab_name_input.text}
            if self.prefab_spawn_button.check_click(mouse_pos):
                return {'action': 'spawn_prefab', 'prefab': self.prefab_name_input.text}
            for rect, scene_path in self.scene_quick_rects:
                if rect.collidepoint(mouse_pos):
                    return {'action': 'load_scene', 'scene': scene_path}
            for rect, prefab_name in self.prefab_quick_rects:
                if rect.collidepoint(mouse_pos):
                    return {'action': 'spawn_prefab', 'prefab': prefab_name}

            scripts_info = self.prop_inputs.get('scripts')
            if scripts_info:
                if scripts_info.get('add_btn') and scripts_info['add_btn'].check_click(mouse_pos):
                    field = scripts_info.get('field')
                    entered = field.text if field else ''
                    scripts = normalize_script_names(entered)
                    if scripts:
                        self._script_confirmation = {'mode': 'add', 'scripts': scripts}
                    return None

                if scripts_info.get('remove_btn') and scripts_info['remove_btn'].check_click(mouse_pos):
                    field = scripts_info.get('field')
                    entered = field.text if field else ''
                    scripts = normalize_script_names(entered)
                    if scripts:
                        self._script_confirmation = {'mode': 'remove', 'scripts': scripts}
                    return None

                if scripts_info.get('confirm_yes_btn') and scripts_info['confirm_yes_btn'].check_click(mouse_pos):
                    if self._script_confirmation:
                        action = {
                            'action': 'scripts_apply',
                            'mode': self._script_confirmation['mode'],
                            'scripts': list(self._script_confirmation['scripts']),
                        }
                        self._script_confirmation = None
                        return action

                if scripts_info.get('confirm_no_btn') and scripts_info['confirm_no_btn'].check_click(mouse_pos):
                    self._script_confirmation = None
                    return None

            # Spawn buttons → enter placement mode
            for spawn_type, btn in self.spawn_buttons.items():
                if btn.check_click(mouse_pos):
                    if self.placement_mode == spawn_type:
                        # Toggle off
                        self.placement_mode = None
                    else:
                        self.placement_mode = spawn_type
                    return None  # consumed

            # Collapsible section toggles
            self.section_settings.toggle(mouse_pos)
            if self.section_settings.expanded:
                self.section_ps2.toggle(mouse_pos)
                self.section_sun.toggle(mouse_pos)
                self.section_shadows.toggle(mouse_pos)

            # Model dropdown and buttons
            if self.model_dropdown.handle_event(event): return None
            if self.model_refresh_btn.check_click(mouse_pos):
                base_path = self.model_path_input.text or "models"
                self.refresh_models(base_path)
            if self.model_spawn_btn.check_click(mouse_pos):
                selected = self.model_dropdown.selected
                if selected and selected != "(no models found)" and selected != "(select model)":
                    model_path = self.model_path_input.text + selected
                    return {'action': 'spawn_model', 'model': model_path}

            # Save As button
            if self.save_as_button.check_click(mouse_pos):
                return {'action': 'save_as', 'filename': self.save_as_input.text}

            # Autosave toggle
            if self.autosave_toggle_rect.collidepoint(mouse_pos):
                self.autosave_enabled = not self.autosave_enabled
                return {'action': 'autosave_toggle', 'enabled': self.autosave_enabled}

            # Retro toggles (no immediate engine action; engine reads values each frame)
            for key in (
                'ps2_toggle_rect',
                'postprocess_toggle_rect',
                'quantize_toggle_rect',
                'dither_toggle_rect',
                'lighting_ramp_toggle_rect',
                'specular_toggle_rect',
                'wobble_toggle_rect',
                'directional_shadows_toggle_rect',
                'spot_shadows_toggle_rect',
            ):
                rect = getattr(self, key, None)
                if rect and rect.collidepoint(mouse_pos):
                    if key == 'ps2_toggle_rect':
                        self.ps2_enabled = not self.ps2_enabled
                    elif key == 'postprocess_toggle_rect':
                        self.postprocess_enabled = not self.postprocess_enabled
                    elif key == 'quantize_toggle_rect':
                        self.quantize_enabled = not self.quantize_enabled
                    elif key == 'dither_toggle_rect':
                        self.dither_enabled = not self.dither_enabled
                    elif key == 'lighting_ramp_toggle_rect':
                        self.lighting_ramp_enabled = not self.lighting_ramp_enabled
                    elif key == 'specular_toggle_rect':
                        self.specular_banding_enabled = not self.specular_banding_enabled
                    elif key == 'wobble_toggle_rect':
                        self.wobble_enabled = not self.wobble_enabled
                    elif key == 'directional_shadows_toggle_rect':
                        self.directional_shadows_enabled = not self.directional_shadows_enabled
                    elif key == 'spot_shadows_toggle_rect':
                        self.spot_shadows_enabled = not self.spot_shadows_enabled
                    return None

            # --- Animation Recording Buttons ---
            if self.record_btn.check_click(mouse_pos):
                return {'action': 'anim_record_toggle'}
            if self.play_btn.check_click(mouse_pos):
                return {'action': 'anim_play', 'name': self.recording_name_input.text}
            if self.stop_btn.check_click(mouse_pos):
                return {'action': 'anim_stop'}
            if self.clear_btn.check_click(mouse_pos):
                return {'action': 'anim_clear'}
            if self.save_anim_btn.check_click(mouse_pos):
                return {
                    'action': 'anim_save', 
                    'name': self.recording_name_input.text,
                    'smooth': self.anim_smooth
                }

            # Check smooth toggle click
            if hasattr(self, 'anim_smooth_rect') and self.anim_smooth_rect.collidepoint(mouse_pos):
                self.anim_smooth = not self.anim_smooth
                return None

        # Cutscene section toggle
        if self.section_cutscene.toggle(mouse_pos):
            return None

        # Cutscene controls (only when expanded)
        if self.section_cutscene.expanded:
            if self.cutscene_add_point_btn.check_click(mouse_pos):
                return {'action': 'cutscene_add_point'}
            if self.cutscene_play_btn.check_click(mouse_pos):
                return {'action': 'cutscene_play'}
            if self.cutscene_stop_btn.check_click(mouse_pos):
                return {'action': 'cutscene_stop'}
            if self.cutscene_clear_btn.check_click(mouse_pos):
                return {'action': 'cutscene_clear'}
            if self.cutscene_save_btn.check_click(mouse_pos):
                return {'action': 'cutscene_save', 'name': self.cutscene_name_input.text}
            if self.cutscene_load_btn.check_click(mouse_pos):
                return {'action': 'cutscene_load', 'name': self.cutscene_dropdown.selected}
            if self.cutscene_can_player_move_rect.collidepoint(mouse_pos):
                self.cutscene_can_player_move = not self.cutscene_can_player_move
                return None
            if self.cutscene_loop_rect.collidepoint(mouse_pos):
                self.cutscene_is_looping = not self.cutscene_is_looping
                return None
            if self.cutscene_dropdown.handle_event(event): return None

        # Sprite section toggle
        if self.section_sprite.toggle(mouse_pos):
            return None

        # Sprite controls (only when expanded)
        if self.section_sprite.expanded:
            if self.sprite_spawn_btn.check_click(mouse_pos):
                return {
                    'action': 'spawn_sprite',
                    'path': self.sprite_path_input.text,
                    'name': self.sprite_name_input.text,
                    'billboard': self.sprite_billboard,
                    'autocrop': self.sprite_autocrop,
                }
            if self.sprite_billboard_rect.collidepoint(mouse_pos):
                self.sprite_billboard = not self.sprite_billboard
                return None
            if self.sprite_autocrop_rect.collidepoint(mouse_pos):
                self.sprite_autocrop = not self.sprite_autocrop
                return None

        # Forward to text inputs
        self.save_as_input.handle_event(event)
        self.global_gravity_input.handle_event(event)
        self.scene_load_input.handle_event(event)
        self.prefab_name_input.handle_event(event)
        self.pixel_size_input.handle_event(event)
        self.quantize_steps_input.handle_event(event)
        self.lighting_ramp_steps_input.handle_event(event)
        self.specular_steps_input.handle_event(event)
        self.wobble_pixel_input.handle_event(event)
        self.directional_shadow_resolution_input.handle_event(event)
        self.directional_shadow_distance_input.handle_event(event)
        self.shadow_bias_input.handle_event(event)
        self.spot_shadow_resolution_input.handle_event(event)
        self.ambient_strength_input.handle_event(event)
        self.ambient_color_input.handle_event(event)
        self.sun_azimuth_input.handle_event(event)
        self.sun_elevation_input.handle_event(event)
        self.sun_intensity_input.handle_event(event)
        self.recording_name_input.handle_event(event)
        self.anim_interval.handle_event(event)
        self.cutscene_name_input.handle_event(event)
        self.cutscene_speed_input.handle_event(event)
        self.sprite_path_input.handle_event(event)
        self.sprite_name_input.handle_event(event)

        # Prop inputs processing
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Handle toggles
            for key in ['use_gravity', 'is_kinematic', 'use_anim_state_controller', 'casts_shadows', 'receives_shadows', 'light_casts_shadows', 'interactable']:
                if key in self.prop_inputs and 'toggle_rect' in self.prop_inputs[key]:
                    if self.prop_inputs[key]['toggle_rect'].collidepoint(mouse_pos):
                        self.prop_inputs[key]['value'] = not self.prop_inputs[key]['value']

        for key, info in self.prop_inputs.items():
            if info['field'] and info['field'] != 'toggle':
                info['field'].handle_event(event)

        return None

    def update(self, dt, mouse_pos, selected_obj=None):
        if not self.visible:
            return

        for btn in self.spawn_buttons.values():
            btn.check_hover(mouse_pos)
        self.save_as_button.check_hover(mouse_pos)
        self.undo_button.check_hover(mouse_pos)
        self.redo_button.check_hover(mouse_pos)
        self.scene_load_button.check_hover(mouse_pos)
        self.scene_reload_button.check_hover(mouse_pos)
        self.save_current_button.check_hover(mouse_pos)
        self.prefab_save_button.check_hover(mouse_pos)
        self.prefab_spawn_button.check_hover(mouse_pos)

        self.record_btn.check_hover(mouse_pos)
        self.play_btn.check_hover(mouse_pos)
        self.stop_btn.check_hover(mouse_pos)
        self.clear_btn.check_hover(mouse_pos)
        self.save_anim_btn.check_hover(mouse_pos)

        self.cutscene_add_point_btn.check_hover(mouse_pos)
        self.cutscene_play_btn.check_hover(mouse_pos)
        self.cutscene_stop_btn.check_hover(mouse_pos)
        self.cutscene_clear_btn.check_hover(mouse_pos)
        self.cutscene_save_btn.check_hover(mouse_pos)
        self.cutscene_load_btn.check_hover(mouse_pos)

        self.sprite_spawn_btn.check_hover(mouse_pos)

        self._build_property_inputs(selected_obj)

        self.save_as_input.update(dt)
        self.global_gravity_input.update(dt)
        self.scene_load_input.update(dt)
        self.prefab_name_input.update(dt)
        self.pixel_size_input.update(dt)
        self.quantize_steps_input.update(dt)
        self.lighting_ramp_steps_input.update(dt)
        self.specular_steps_input.update(dt)
        self.wobble_pixel_input.update(dt)
        self.directional_shadow_resolution_input.update(dt)
        self.directional_shadow_distance_input.update(dt)
        self.shadow_bias_input.update(dt)
        self.spot_shadow_resolution_input.update(dt)
        self.ambient_strength_input.update(dt)
        self.ambient_color_input.update(dt)
        self.sun_azimuth_input.update(dt)
        self.sun_elevation_input.update(dt)
        self.sun_intensity_input.update(dt)
        self.recording_name_input.update(dt)
        self.anim_interval.update(dt)
        self.cutscene_name_input.update(dt)
        self.cutscene_speed_input.update(dt)
        self.sprite_path_input.update(dt)
        self.sprite_name_input.update(dt)
        for key, info in self.prop_inputs.items():
            if info['field'] and info['field'] != 'toggle':
                info['field'].update(dt)

        scripts_info = self.prop_inputs.get('scripts')
        if scripts_info:
            for btn_key in ('add_btn', 'remove_btn', 'confirm_yes_btn', 'confirm_no_btn'):
                btn = scripts_info.get(btn_key)
                if btn:
                    btn.check_hover(mouse_pos)

    def read_property_values(self):
        values = {}
        for key, info in self.prop_inputs.items():
            if info['field'] == 'toggle':
                values[key] = info['value']
            elif info['field']:
                values[key] = info['field'].text
        return values

    def refresh_values(self, obj):
        if obj is None:
            return
        pos = obj.position
        scl = obj.scale
        rot = obj.rotation_euler
        field_map = {
            'pos_x': f'{pos.x:.2f}', 'pos_y': f'{pos.y:.2f}', 'pos_z': f'{pos.z:.2f}',
            'rot_x': f'{rot.x:.1f}', 'rot_y': f'{rot.y:.1f}', 'rot_z': f'{rot.z:.1f}',
            'scl_x': f'{scl.x:.3f}', 'scl_y': f'{scl.y:.3f}', 'scl_z': f'{scl.z:.3f}',
        }
        for key, val in field_map.items():
            if key in self.prop_inputs:
                info = self.prop_inputs[key]
                if info['field'] and not info['field'].active:
                    info['field'].text = val
        if 'scripts' in self.prop_inputs:
            self.prop_inputs['scripts']['attached'] = normalize_script_names(
                getattr(obj, 'scripts', [])
            )
        if 'use_anim_state_controller' in self.prop_inputs:
            self.prop_inputs['use_anim_state_controller']['value'] = bool(
                getattr(obj, 'use_anim_state_controller', False)
            )
        cfg = getattr(obj, 'anim_state_config', None)
        if isinstance(cfg, dict):
            map_keys = {
                'anim_idle': str(cfg.get('idle', 'idle')),
                'anim_run': str(cfg.get('run', 'run')),
                'anim_jump': str(cfg.get('jump', 'jump')),
                'anim_fall': str(cfg.get('fall', 'fall')),
                'anim_move_threshold': f"{float(cfg.get('move_threshold', 0.1)):.3f}",
                'anim_vertical_threshold': f"{float(cfg.get('vertical_threshold', 0.15)):.3f}",
            }
            for key, val in map_keys.items():
                if key in self.prop_inputs:
                    info = self.prop_inputs[key]
                    if info.get('field') and not info['field'].active:
                        info['field'].text = val

    def is_point_on_panel(self, pos):
        if not self.visible:
            return False
        panel_rect = pygame.Rect(self.panel_x, self.panel_y,
                                 PANEL_WIDTH, self.win_size[1] - 20)
        return panel_rect.collidepoint(pos)

    def has_active_input(self):
        if (
            self.save_as_input.active
            or self.global_gravity_input.active
            or self.scene_load_input.active
            or self.prefab_name_input.active
            or self.pixel_size_input.active
            or self.quantize_steps_input.active
            or self.lighting_ramp_steps_input.active
            or self.specular_steps_input.active
            or self.wobble_pixel_input.active
            or self.directional_shadow_resolution_input.active
            or self.directional_shadow_distance_input.active
            or self.shadow_bias_input.active
            or self.spot_shadow_resolution_input.active
            or self.ambient_strength_input.active
            or self.ambient_color_input.active
            or self.sun_azimuth_input.active
            or self.sun_elevation_input.active
            or self.sun_intensity_input.active
            or self.recording_name_input.active
            or self.anim_interval.active
            or self.cutscene_name_input.active
            or self.cutscene_speed_input.active
            or self.sprite_path_input.active
            or self.sprite_name_input.active
            or self.model_path_input.active
        ):
            return True
        for key, info in self.prop_inputs.items():
            if info['field'] and info['field'] != 'toggle' and info['field'].active:
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

        clip_rect = pygame.Rect(self.panel_x + 2, self.panel_y + 2, PANEL_WIDTH - 4, panel_h - 4)
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        y = self.panel_y + PANEL_PADDING - self.scroll_y
        bx = self.panel_x + PANEL_PADDING
        bw = PANEL_WIDTH - PANEL_PADDING * 2

        # ── Title ──
        title_surf = self.font_section.render("EDITOR", True, SECTION_COLOR[:3])
        surface.blit(title_surf, (bx, y))
        y += 28

        # History actions
        hist_w = (bw - 8) // 2
        self.undo_button.rect = pygame.Rect(bx, y, hist_w, INPUT_HEIGHT)
        self.redo_button.rect = pygame.Rect(bx + hist_w + 8, y, hist_w, INPUT_HEIGHT)
        self.undo_button.draw(surface, self.font)
        self.redo_button.draw(surface, self.font)
        y += INPUT_HEIGHT + 10

        # ==============================================================
        # TOP: Scene / global settings
        # ==============================================================

        # ── Scene Management ──
        section_surf = self.font_bold.render("── Scene Management ──", True, (100, 200, 255))
        surface.blit(section_surf, (bx, y))
        y += 20

        cur = self.current_scene_file if self.current_scene_file else "(none)"
        cur_surf = self.font.render(f"Current: {cur}", True, LABEL_COLOR[:3])
        surface.blit(cur_surf, (bx, y))
        y += 18

        self.scene_load_input.rect = pygame.Rect(bx, y, bw, INPUT_HEIGHT)
        self.scene_load_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        btn_w = (bw - 8) // 2
        self.scene_load_button.rect = pygame.Rect(bx, y, btn_w, INPUT_HEIGHT)
        self.scene_reload_button.rect = pygame.Rect(bx + btn_w + 8, y, btn_w, INPUT_HEIGHT)
        self.scene_load_button.draw(surface, self.font)
        self.scene_reload_button.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        self.save_current_button.rect = pygame.Rect(bx, y, bw, INPUT_HEIGHT)
        self.save_current_button.draw(surface, self.font)
        y += INPUT_HEIGHT + 8

        self.scene_quick_rects = []
        quick_title = self.font.render("Quick Load:", True, (130, 130, 160))
        surface.blit(quick_title, (bx, y))
        y += 16
        for scene_path in self.available_scenes[:8]:
            name = os.path.basename(scene_path)
            btn_rect = pygame.Rect(bx, y, bw, 20)
            hover = btn_rect.collidepoint(pygame.mouse.get_pos())
            bg_c = BUTTON_HOVER if hover else BUTTON_BG
            pygame.draw.rect(surface, bg_c, btn_rect, border_radius=3)
            pygame.draw.rect(surface, INPUT_BORDER, btn_rect, 1, border_radius=3)
            txt = self.font.render(name, True, BUTTON_TEXT[:3])
            surface.blit(txt, (bx + 6, y + 2))
            self.scene_quick_rects.append((btn_rect, scene_path))
            y += 24
        y += 6

        # ── Prefabs ──
        section_surf = self.font_bold.render("── Prefabs ──", True, (100, 200, 255))
        surface.blit(section_surf, (bx, y))
        y += 20

        self.prefab_name_input.rect = pygame.Rect(bx, y, bw, INPUT_HEIGHT)
        self.prefab_name_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        pbtn_w = (bw - 8) // 2
        self.prefab_save_button.rect = pygame.Rect(bx, y, pbtn_w, INPUT_HEIGHT)
        self.prefab_spawn_button.rect = pygame.Rect(bx + pbtn_w + 8, y, pbtn_w, INPUT_HEIGHT)
        self.prefab_save_button.draw(surface, self.font)
        self.prefab_spawn_button.draw(surface, self.font)
        y += INPUT_HEIGHT + 6

        self.prefab_quick_rects = []
        quick_prefab = self.font.render("Quick Spawn:", True, (130, 130, 160))
        surface.blit(quick_prefab, (bx, y))
        y += 16
        for prefab_name in self.available_prefabs[:8]:
            p_rect = pygame.Rect(bx, y, bw, 20)
            hover = p_rect.collidepoint(pygame.mouse.get_pos())
            bg_c = BUTTON_HOVER if hover else BUTTON_BG
            pygame.draw.rect(surface, bg_c, p_rect, border_radius=3)
            pygame.draw.rect(surface, INPUT_BORDER, p_rect, 1, border_radius=3)
            txt = self.font.render(prefab_name, True, BUTTON_TEXT[:3])
            surface.blit(txt, (bx + 6, y + 2))
            self.prefab_quick_rects.append((p_rect, prefab_name))
            y += 24
        y += 6

        # ── Spawn (click to place) ──
        section_surf = self.font_bold.render("── Spawn ──", True, (100, 200, 255))
        surface.blit(section_surf, (bx, y))
        y += 22

        for spawn_type, btn in self.spawn_buttons.items():
            btn.rect.y = y
            is_active = (self.placement_mode == spawn_type)
            btn.draw(surface, self.font, active=is_active)
            y += BUTTON_HEIGHT + 6

        # ── Model Spawn ──
        model_label = self.font.render("Import Model:", True, (130, 180, 255))
        surface.blit(model_label, (bx, y))
        y += 20

        self.model_path_input.rect = pygame.Rect(bx, y, bw, INPUT_HEIGHT)
        self.model_path_input.draw(surface, self.font)
        y += INPUT_HEIGHT + 4

        self.model_refresh_btn.rect = pygame.Rect(bx, y, 70, INPUT_HEIGHT)
        self.model_refresh_btn.draw(surface, self.font)
        
        self.model_dropdown.rect.x = bx + 76
        self.model_dropdown.rect.width = bw - 76
        y = self.model_dropdown.draw(surface, self.font, bx + 76, y) - 4

        self.model_spawn_btn.rect = pygame.Rect(bx, y, bw, INPUT_HEIGHT)
        self.model_spawn_btn.draw(surface, self.font)
        y += INPUT_HEIGHT + 4
        
        model_hint = self.font.render("Select or type model path", True, (120, 120, 140))
        surface.blit(model_hint, (bx, y))
        y += 18

        # Placement hint
        if self.placement_mode:
            hint = self.font.render(
                f"Click viewport to place {self.placement_mode}",
                True, (0, 255, 120)
            )
            surface.blit(hint, (bx, y))
            y += 18
        y += 6

        # ── Settings ──
        y += 4
        y = self.section_settings.draw(surface, self.font_bold, bx, y)
        
        if self.section_settings.expanded:
            # Autosave toggle
            label = self.font.render("Autosave (30s)", True, LABEL_COLOR[:3])
            surface.blit(label, (bx, y + 2))

            toggle_x = bx + bw - 44
            self.autosave_toggle_rect = pygame.Rect(toggle_x, y, 40, 22)
            bg_c = TOGGLE_ON if self.autosave_enabled else TOGGLE_OFF
            pygame.draw.rect(surface, bg_c, self.autosave_toggle_rect, border_radius=11)
            knob_x = toggle_x + 20 if self.autosave_enabled else toggle_x + 2
            pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 11), 8)
            y += 30

            # Global gravity input
            label = self.font.render("Gravity", True, LABEL_COLOR[:3])
            surface.blit(label, (bx, y + 4))
            self.global_gravity_input.rect = pygame.Rect(bx + 80, y, bw - 80, INPUT_HEIGHT)
            self.global_gravity_input.draw(surface, self.font)
            y += INPUT_HEIGHT + 10
            
            # Collapsible subsections
            y = self._draw_ps2_section(surface, bx, bw, y)
            y = self._draw_sun_section(surface, bx, bw, y)
            y = self._draw_shadows_section(surface, bx, bw, y)

        # Particles section moved to separate panel (F4 to toggle)

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
        y += INPUT_HEIGHT + 16

        # ── Cutscene Maker ──
        y = self.section_cutscene.draw(surface, self.font_bold, bx, y)
        if self.section_cutscene.expanded:
            y = self._draw_cutscene_section(surface, bx, bw, y)

        # ── Sprite Spawner ──
        y = self.section_sprite.draw(surface, self.font_bold, bx, y)
        if self.section_sprite.expanded:
            y = self._draw_sprite_section(surface, bx, bw, y)

        # ── Capabilities ──
        section_surf = self.font_bold.render("── Capabilities ──", True, (100, 200, 255))
        surface.blit(section_surf, (bx, y))
        y += 20
        for line in (
            "F1: Toggle Play/Edit",
            "F2: Toggle Cursor/FPS",
            "F3: Toggle Hierarchy",
            "Ctrl+S: Save scene",
            "Delete: Remove selected",
            "C (FPS mode): Spawn cube",
        ):
            txt = self.font.render(line, True, (150, 150, 170))
            surface.blit(txt, (bx, y))
            y += 16
        y += 12

        # ==============================================================
        # BOTTOM: Selected object inspector
        # ==============================================================
        sep_y = y
        pygame.draw.line(surface, (80, 120, 100), (bx, sep_y), (bx + bw, sep_y), 2)
        y += 10

        if self._current_obj_name and self.prop_inputs:
            section_surf = self.font_bold.render(
                f"── Selected Object: {self._current_obj_name} ──", True, (120, 230, 170)
            )
            surface.blit(section_surf, (bx, y))
            y += 24
            y = self._draw_properties(surface, y, bx, bw)
            y += 8
        else:
            section_surf = self.font_bold.render("── Selected Object ──", True, (120, 230, 170))
            surface.blit(section_surf, (bx, y))
            y += 22
            hint = self.font.render("No object selected.", True, (140, 140, 150))
            surface.blit(hint, (bx, y))
            y += 16
            hint2 = self.font.render("Click an object to edit its properties.", True, (120, 120, 130))
            surface.blit(hint2, (bx, y))
            y += 22

        content_h = y + self.scroll_y - self.panel_y
        self.max_scroll = max(0, content_h - panel_h + 20)
        surface.set_clip(old_clip)

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

        # Rotation
        label_surf = self.font_bold.render("Rotation", True, LABEL_COLOR[:3])
        surface.blit(label_surf, (bx, y))
        y += 18

        x = bx
        for key in ['rot_x', 'rot_y', 'rot_z']:
            if key in self.prop_inputs:
                info = self.prop_inputs[key]
                lbl_c = {'rot_x': (255, 80, 80), 'rot_y': (80, 255, 80), 'rot_z': (80, 80, 255)}
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

        # --- Physics Layouts ---
        
        # Numeric physics fields side by side
        phys_keys = ['mass', 'bounciness', 'friction', 'drag']
        if all(k in self.prop_inputs for k in phys_keys):
            label_surf = self.font_bold.render("Physics", True, (255, 150, 50))
            surface.blit(label_surf, (bx, y))
            y += 18
            
            x = bx
            for key in phys_keys:
                info = self.prop_inputs[key]
                lbl = self.font_bold.render(info['label'], True, LABEL_COLOR[:3])
                surface.blit(lbl, (x, y + 3))
                if info['field'] is None:
                    info['field'] = TextInput(x + 16, y, single_w, INPUT_HEIGHT,
                                              info['label'], info['value'])
                info['field'].rect = pygame.Rect(x + 16, y, single_w, INPUT_HEIGHT)
                info['field'].draw(surface, self.font)
                x += single_w + 24
            y += INPUT_HEIGHT + 10

        # Toggle Physics fields side by side
        tog_keys = ['is_kinematic', 'use_gravity', 'casts_shadows', 'receives_shadows']
        if all(k in self.prop_inputs for k in tog_keys):
            x = bx
            for key in tog_keys:
                info = self.prop_inputs[key]
                lbl = self.font_bold.render(info['label'], True, LABEL_COLOR[:3])
                surface.blit(lbl, (x, y + 2))
                
                toggle_x = x + 75
                toggle_rect = pygame.Rect(toggle_x, y, 36, 18)
                self.prop_inputs[key]['toggle_rect'] = toggle_rect
                
                is_on = info['value']
                bg_c = TOGGLE_ON if is_on else TOGGLE_OFF
                pygame.draw.rect(surface, bg_c, toggle_rect, border_radius=9)
                knob_x = toggle_x + 18 if is_on else toggle_x + 2
                pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)
                
                x += single_w + 40
                if x > bx + bw - 110:
                    x = bx
                    y += 24
            y += 24

        if 'light_casts_shadows' in self.prop_inputs:
            info = self.prop_inputs['light_casts_shadows']
            lbl = self.font_bold.render(info['label'], True, LABEL_COLOR[:3])
            surface.blit(lbl, (bx, y + 2))
            toggle_x = bx + 100
            toggle_rect = pygame.Rect(toggle_x, y, 36, 18)
            info['toggle_rect'] = toggle_rect
            is_on = info['value']
            bg_c = TOGGLE_ON if is_on else TOGGLE_OFF
            pygame.draw.rect(surface, bg_c, toggle_rect, border_radius=9)
            knob_x = toggle_x + 18 if is_on else toggle_x + 2
            pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)
            y += 24

        # Interaction
        if 'interactable' in self.prop_inputs:
            info = self.prop_inputs['interactable']
            lbl = self.font_bold.render("Interactable", True, (100, 220, 160))
            surface.blit(lbl, (bx, y + 2))
            toggle_x = bx + 100
            toggle_rect = pygame.Rect(toggle_x, y, 36, 18)
            info['toggle_rect'] = toggle_rect
            is_on = info['value']
            bg_c = TOGGLE_ON if is_on else TOGGLE_OFF
            pygame.draw.rect(surface, bg_c, toggle_rect, border_radius=9)
            knob_x = toggle_x + 18 if is_on else toggle_x + 2
            pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)
            y += 24

        if 'interaction_distance' in self.prop_inputs:
            info = self.prop_inputs['interaction_distance']
            label_surf = self.font_bold.render("Interact Dist", True, (100, 220, 160))
            surface.blit(label_surf, (bx, y))
            y += 18
            full_w = PANEL_WIDTH - PANEL_PADDING * 2 - 10
            if info['field'] is None:
                info['field'] = TextInput(bx, y, full_w, INPUT_HEIGHT, 'Dist', info['value'])
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

        # Scripts
        if 'scripts' in self.prop_inputs:
            info = self.prop_inputs['scripts']
            label_surf = self.font_bold.render("Scripts (names only)", True, (100, 200, 255))
            surface.blit(label_surf, (bx, y))
            y += 18

            full_w = PANEL_WIDTH - PANEL_PADDING * 2 - 10
            if info['field'] is None:
                info['field'] = TextInput(bx, y, full_w, INPUT_HEIGHT,
                                          'Scripts', info['value'])
            info['field'].rect = pygame.Rect(bx, y, full_w, INPUT_HEIGHT)
            info['field'].draw(surface, self.font)
            y += INPUT_HEIGHT + 10

            btn_w = (full_w - 8) // 2
            if info.get('add_btn') is None:
                info['add_btn'] = Button(bx, y, btn_w, INPUT_HEIGHT, "Add")
            if info.get('remove_btn') is None:
                info['remove_btn'] = Button(bx + btn_w + 8, y, btn_w, INPUT_HEIGHT, "Remove")
            info['add_btn'].rect = pygame.Rect(bx, y, btn_w, INPUT_HEIGHT)
            info['remove_btn'].rect = pygame.Rect(bx + btn_w + 8, y, btn_w, INPUT_HEIGHT)
            info['add_btn'].draw(surface, self.font)
            info['remove_btn'].draw(surface, self.font)
            y += INPUT_HEIGHT + 8

            hint = self.font.render("Type names, then click Add/Remove", True, (130, 130, 160))
            surface.blit(hint, (bx, y))
            y += 18

            if self._script_confirmation:
                mode_label = "ADD" if self._script_confirmation['mode'] == 'add' else "REMOVE"
                names_text = ", ".join(self._script_confirmation['scripts'])
                conf = self.font.render(f"Confirm {mode_label}: {names_text}", True, (255, 220, 120))
                surface.blit(conf, (bx, y))
                y += 18

                yes_w = (full_w - 8) // 2
                if info.get('confirm_yes_btn') is None:
                    info['confirm_yes_btn'] = Button(bx, y, yes_w, INPUT_HEIGHT, "Confirm")
                if info.get('confirm_no_btn') is None:
                    info['confirm_no_btn'] = Button(bx + yes_w + 8, y, yes_w, INPUT_HEIGHT, "Cancel")
                info['confirm_yes_btn'].rect = pygame.Rect(bx, y, yes_w, INPUT_HEIGHT)
                info['confirm_no_btn'].rect = pygame.Rect(bx + yes_w + 8, y, yes_w, INPUT_HEIGHT)
                info['confirm_yes_btn'].draw(surface, self.font, active=True)
                info['confirm_no_btn'].draw(surface, self.font)
                y += INPUT_HEIGHT + 8
            else:
                info.pop('confirm_yes_btn', None)
                info.pop('confirm_no_btn', None)

            attached = normalize_script_names(info.get('attached', []))
            if attached:
                list_label = self.font.render("Attached:", True, (180, 180, 220))
                surface.blit(list_label, (bx, y))
                y += 16
                for s in attached:
                    script_lbl = self.font.render(f"- {s}", True, (180, 180, 220))
                    surface.blit(script_lbl, (bx + 10, y))
                    y += 16
                y += 8
            else:
                none_lbl = self.font.render("Attached: (none)", True, (140, 140, 140))
                surface.blit(none_lbl, (bx, y))
                y += 20

        # Animation state controller
        if 'use_anim_state_controller' in self.prop_inputs:
            label_surf = self.font_bold.render("Animation Controller", True, (180, 210, 255))
            surface.blit(label_surf, (bx, y))
            y += 18

            info = self.prop_inputs['use_anim_state_controller']
            lbl = self.font_bold.render(info['label'], True, LABEL_COLOR[:3])
            surface.blit(lbl, (bx, y + 2))
            toggle_x = bx + 88
            toggle_rect = pygame.Rect(toggle_x, y, 36, 18)
            info['toggle_rect'] = toggle_rect
            is_on = info['value']
            bg_c = TOGGLE_ON if is_on else TOGGLE_OFF
            pygame.draw.rect(surface, bg_c, toggle_rect, border_radius=9)
            knob_x = toggle_x + 18 if is_on else toggle_x + 2
            pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)
            y += 24

            anim_keys = [
                ('anim_idle', 'Idle Clip'),
                ('anim_run', 'Run Clip'),
                ('anim_jump', 'Jump Clip'),
                ('anim_fall', 'Fall Clip'),
                ('anim_move_threshold', 'Move Thresh'),
                ('anim_vertical_threshold', 'Vert Thresh'),
            ]
            full_w = PANEL_WIDTH - PANEL_PADDING * 2 - 10
            for key, label in anim_keys:
                if key not in self.prop_inputs:
                    continue
                info = self.prop_inputs[key]
                lbl = self.font.render(label, True, LABEL_COLOR[:3])
                surface.blit(lbl, (bx, y + 4))
                if info['field'] is None:
                    info['field'] = TextInput(bx + 100, y, full_w - 100, INPUT_HEIGHT, label, info['value'])
                info['field'].rect = pygame.Rect(bx + 100, y, full_w - 100, INPUT_HEIGHT)
                info['field'].draw(surface, self.font)
                y += INPUT_HEIGHT + 6
            y += 4

        y = self._draw_animation_section(surface, y, bx, bw)
        return y

    def _draw_animation_section(self, surface, y, bx, bw):
        """Draw animation recording and clip list. Returns new y."""
        label_surf = self.font_bold.render("Animation Recording", True, (255, 100, 150))
        surface.blit(label_surf, (bx, y))
        y += 22

        # Recording Name
        self.recording_name_input.rect = pygame.Rect(bx, y, bw - 80, INPUT_HEIGHT)
        self.recording_name_input.draw(surface, self.font)
        
        self.save_anim_btn.rect = pygame.Rect(bx + bw - 70, y, 70, INPUT_HEIGHT)
        self.save_anim_btn.draw(surface, self.font)
        y += INPUT_HEIGHT + 10

        # Control Buttons
        btn_w = 70
        spacing = 8
        self.record_btn.rect = pygame.Rect(bx, y, btn_w, INPUT_HEIGHT)
        self.play_btn.rect = pygame.Rect(bx + btn_w + spacing, y, btn_w, INPUT_HEIGHT)
        self.stop_btn.rect = pygame.Rect(bx + (btn_w + spacing) * 2, y, btn_w, INPUT_HEIGHT)
        self.clear_btn.rect = pygame.Rect(bx + (btn_w + spacing) * 3, y, btn_w, INPUT_HEIGHT)

        self.record_btn.draw(surface, self.font, active=self.is_recording)
        self.play_btn.draw(surface, self.font)
        self.stop_btn.draw(surface, self.font)
        self.clear_btn.draw(surface, self.font)
        y += INPUT_HEIGHT + 10

        # Smoothing and Interval
        label = self.font.render("Smooth", True, LABEL_COLOR[:3])
        surface.blit(label, (bx, y + 2))
        toggle_x = bx + 60
        self.anim_smooth_rect = pygame.Rect(toggle_x, y, 36, 18)
        bg_c = (0, 200, 100) if self.anim_smooth else (100, 100, 100)
        pygame.draw.rect(surface, bg_c, self.anim_smooth_rect, border_radius=9)
        knob_x = toggle_x + 18 if self.anim_smooth else toggle_x + 2
        pygame.draw.circle(surface, (255, 255, 255), (knob_x + 9, y + 9), 6)
        
        # Move interval to the right
        label = self.font.render("Interval", True, LABEL_COLOR[:3])
        label_w = label.get_width()
        surface.blit(label, (bx + bw - (label_w + 60), y + 4))
        self.anim_interval.rect = pygame.Rect(bx + bw - 50, y, 50, INPUT_HEIGHT)
        self.anim_interval.draw(surface, self.font)
        y += INPUT_HEIGHT + 10

        # Keyframe count
        kf_count = len(self.recorded_keyframes)
        kf_txt = self.font.render(f"Keyframes recorded: {kf_count}", True, LABEL_COLOR[:3])
        surface.blit(kf_txt, (bx, y))
        y += 18

        # Clip List (if object has animator)
        info = self.prop_inputs.get('animation_clips')
        if info:
            y += 4
            section_label = self.font_bold.render("Available Clips", True, (100, 200, 255))
            surface.blit(section_label, (bx, y))
            y += 20
            for name in info['clips']:
                clip_rect = pygame.Rect(bx, y, bw, 20)
                # We can make these clickable to play them
                # For now just list them
                pygame.draw.rect(surface, BUTTON_BG, clip_rect, border_radius=3)
                txt = self.font.render(name, True, BUTTON_TEXT[:3])
                surface.blit(txt, (bx + 6, y + 2))
                y += 24
        
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
