"""HUD overlay — renders 2D text/panels on top of the 3D scene using Pygame fonts."""

import os
import pygame
import moderngl


class HUD:
    """On-screen text overlay rendered via Pygame → ModernGL texture."""

    def __init__(self, ctx, win_size):
        self.ctx = ctx
        self.win_size = win_size

        # Load screen-space shader
        shader_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shaders')
        with open(os.path.join(shader_dir, 'screen.vert'), 'r') as f:
            vert_src = f.read()
        with open(os.path.join(shader_dir, 'screen.frag'), 'r') as f:
            frag_src = f.read()
        self.program = ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

        # Empty VAO for procedural full-screen quad
        self.vao = ctx.vertex_array(self.program, [])

        # Pygame font
        pygame.font.init()
        self.font_large = pygame.font.SysFont('Consolas', 28, bold=True)
        self.font_small = pygame.font.SysFont('Consolas', 22)

        # HUD texture (persistent, updated via .write())
        self._texture = None
        self._texture_size = (0, 0)

        # State
        self.show_controls = False
        self.dev_mode = False
        self.selected_name = ""
        self.selected_pos = None
        self.selected_scale = None
        self.stretch_axis = None
        self.editor_ui = None  # set by engine after creation
        self.scene_hierarchy = None  # set by engine after creation
        self.dialogue_manager = None  # set by engine after creation
        self.scene_objects_ref = []  # set each frame by update()
        self._selected_index = -1
        
        # --- Image Overlay State ---
        self._overlay_active = False
        self._overlay_timer = 0.0
        self._overlay_surf = None
        self._overlay_path = None
        self._overlay_fade = 1.0  # Optional: could add fade in/out later

        # --- Task System ---
        self.task_name = "Task: Man im hungry"
        self.task_requirement = "Requirement: Go buy a pizza"

        # --- Prompt Box ---
        self._prompt_active = False
        self._prompt_text = ""
        self._prompt_subtext = ""

    def toggle_controls(self):
        self.show_controls = not self.show_controls

    def update(self, dt):
        """Update timers for HUD effects (like image overlays)."""
        if self._overlay_active:
            self._overlay_timer -= dt
            if self._overlay_timer <= 0:
                self._overlay_active = False
                # Optionally keep the surface cached but stop drawing it

    def show_image(self, path, duration):
        """Display a fullscreen image overlay for a set duration."""
        if not os.path.exists(path):
            print(f"[HUD] ERROR: Overlay image not found: {path}")
            return
            
        try:
            # Load and scale to fit the window exactly
            img = pygame.image.load(path).convert_alpha()
            self._overlay_surf = pygame.transform.smoothscale(img, self.win_size)
            self._overlay_path = path
            self._overlay_timer = duration
            self._overlay_active = True
            print(f"[HUD] Showing overlay: {path} for {duration}s")
        except Exception as e:
            print(f"[HUD] ERROR loading overlay {path}: {e}")

    def set_task(self, name, requirement):
        """Update the on-screen task information."""
        self.task_name = f"Task: {name}"
        self.task_requirement = f"Requirement: {requirement}"
        print(f"[HUD] Task Updated: {name}")

    def show_prompt(self, text, subtext=""):
        self._prompt_text = text
        self._prompt_subtext = subtext
        self._prompt_active = True

    def hide_prompt(self):
        self._prompt_active = False
        self._prompt_text = ""
        self._prompt_subtext = ""

    def render(self):
        """Render the HUD overlay on top of the scene."""
        surface = self._build_surface()
        if surface is None:
            return

        data = pygame.image.tostring(surface, 'RGBA', True)
        w, h = surface.get_size()

        # Create texture once or if size changes, otherwise use .write() to update
        if self._texture is None or (w, h) != self._texture_size:
            if self._texture:
                self._texture.release()
            self._texture = self.ctx.texture((w, h), 4, data)
            self._texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
            self._texture_size = (w, h)
        else:
            self._texture.write(data)

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.ctx.disable(moderngl.DEPTH_TEST)

        self._texture.use(location=0)
        self.program['u_texture'].value = 0
        self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

        self.ctx.disable(moderngl.BLEND)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def _build_surface(self):
        """Create a Pygame surface with the HUD content."""
        surface = pygame.Surface(self.win_size, pygame.SRCALPHA)
        
        # --- Fullscreen Image Overlay ---
        if self._overlay_active and self._overlay_surf:
            surface.blit(self._overlay_surf, (0, 0))

        # Always draw crosshair, rest only in dev mode

        # --- Crosshair (always visible) ---
        cx, cy = self.win_size[0] // 2, self.win_size[1] // 2
        size = 12
        thickness = 2
        color = (255, 255, 255, 180)
        if self.dev_mode:
            color = (0, 255, 100, 220)
        # Horizontal line
        pygame.draw.line(surface, color, (cx - size, cy), (cx + size, cy), thickness)
        # Vertical line
        pygame.draw.line(surface, color, (cx, cy - size), (cx, cy + size), thickness)
        # Center dot
        pygame.draw.circle(surface, color, (cx, cy), 2)

        # Dialogue overlay (renders in play mode which otherwise returns early)
        if self.dialogue_manager and self.dialogue_manager.active:
            self.dialogue_manager.draw(surface, self.font_large, self.font_small,
                                       self.win_size)
            return surface

        if self._prompt_active and self._prompt_text:
            self._draw_prompt(surface)
            return surface

        if not self.dev_mode and not self.show_controls:
            # Even if not in dev mode, draw the task
            self._draw_task(surface)
            return surface

        # Draw task in dev mode too
        self._draw_task(surface)

        y = 10

        # Dev mode indicator
        if self.dev_mode:
            self._draw_text(surface, "[ DEV MODE ]", 10, y, self.font_large,
                            (0, 255, 100, 255))
            y += 28

            # Selected object info
            if self.selected_name:
                self._draw_text(surface, f"Selected: {self.selected_name}", 10, y,
                                self.font_small, (255, 255, 100, 255))
                y += 20
                if self.selected_pos:
                    p = self.selected_pos
                    self._draw_text(surface, f"  Pos: ({p.x:.2f}, {p.y:.2f}, {p.z:.2f})",
                                    10, y, self.font_small, (200, 200, 200, 220))
                    y += 18
                if self.selected_scale:
                    s = self.selected_scale
                    self._draw_text(surface, f"  Scale: ({s.x:.4f}, {s.y:.4f}, {s.z:.4f})",
                                    10, y, self.font_small, (200, 200, 200, 220))
                    y += 18

                # Stretch axis indicator
                if self.stretch_axis:
                    axis_colors = {'X': (255, 80, 80), 'Y': (80, 255, 80), 'Z': (80, 80, 255)}
                    ac = axis_colors.get(self.stretch_axis, (255, 255, 255))
                    self._draw_text(surface, f"  Stretch: {self.stretch_axis} axis",
                                    10, y, self.font_small, (*ac, 255))
                    y += 18
                else:
                    self._draw_text(surface, "  Stretch: uniform (hold 1/2/3 for X/Y/Z)",
                                    10, y, self.font_small, (140, 140, 140, 160))
                    y += 18
            else:
                self._draw_text(surface, "No object selected (click to select)",
                                10, y, self.font_small, (180, 180, 180, 180))
                y += 20

            y += 6
            self._draw_text(surface, "Press H for controls", 10, y,
                            self.font_small, (140, 140, 140, 160))

        # Controls panel
        if self.show_controls:
            self._draw_controls_panel(surface)

        # Editor panel (drawn last, on top)
        if self.editor_ui:
            self.editor_ui.draw(surface)

        # Hierarchy panel (left side)
        if self.scene_hierarchy:
            self.scene_hierarchy.draw(
                surface, self.scene_objects_ref, self._selected_index
            )

        return surface

    def _draw_controls_panel(self, surface):
        """Draw the controls help panel."""
        panel_w, panel_h = 380, 430
        px = self.win_size[0] - panel_w - 20
        py = 20

        # Background
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((15, 15, 25, 210))
        pygame.draw.rect(panel, (0, 200, 120, 180), (0, 0, panel_w, panel_h), 2, border_radius=6)
        surface.blit(panel, (px, py))

        cx = px + 15
        cy = py + 12

        self._draw_text(surface, "CONTROLS", cx, cy, self.font_large, (0, 230, 120, 255))
        cy += 30

        controls = [
            ("Camera", [
                ("WASD", "Move camera"),
                ("Mouse", "Look around"),
                ("Space / LShift", "Fly up / down"),
                ("Escape", "Quit / Free Cursor"),
            ]),
            ("Dev Mode", [
                ("F1", "Toggle dev mode"),
                ("F2", "Toggle cursor mode"),
                ("F3", "Toggle hierarchy pnl"),
                ("H", "Toggle this panel"),
                ("Click", "Select / Place obj"),
                ("+ / -", "Scale (uniform)"),
                ("1/2/3 + scale", "Stretch X / Y / Z"),
                ("Arrows", "Move object XZ"),
                ("Q / E", "Move object Y"),
                ("C", "Spawn cube"),
                ("Delete", "Delete selected"),
                ("Ctrl+S", "Save scene"),
                ("Tab", "Save + print info"),
            ]),
        ]

        for section_name, bindings in controls:
            self._draw_text(surface, f"── {section_name} ──", cx, cy,
                            self.font_small, (100, 200, 255, 220))
            cy += 22
            for key, desc in bindings:
                self._draw_text(surface, f"  {key:<20s}{desc}", cx, cy,
                                self.font_small, (210, 210, 210, 230))
                cy += 19
            cy += 6

    def _draw_task(self, surface):
        """Draw the current task in the top-left corner on a dark panel."""
        # Hide task during cutscenes or image overlays for a clean cinematic look
        if self.engine.cutscenes.is_playing or self._overlay_active:
            return
            
        tx, ty = 20, 20
        pad = 12
        line_h = 24
        
        # Measure text to determine panel size
        name_surf = self.font_large.render(self.task_name, True, (255, 255, 255))
        req_surf = self.font_small.render(self.task_requirement, True, (255, 255, 255))
        
        box_w = max(name_surf.get_width(), req_surf.get_width()) + pad * 2
        box_h = pad * 2 + line_h + 20 # Task + gap + Req
        
        # Draw background panel
        panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150)) # Semi-transparent black
        pygame.draw.rect(panel, (255, 255, 255, 120), panel.get_rect(), 1, border_radius=4)
        surface.blit(panel, (tx - pad, ty - pad))
        
        # Draw Task Name (Bold/Bright)
        surface.blit(name_surf, (tx, ty))
        # Draw Requirement (Slightly smaller/dimmer)
        surface.blit(req_surf, (tx, ty + line_h + 4))

    def _draw_prompt(self, surface):
        """Draw a simple dialogue-style prompt box near the bottom of the screen."""
        sw, sh = self.win_size
        pad = 20
        margin = 40
        line_h = 24
        box_w = sw - margin * 2
        text_lines = [self._prompt_text]
        if self._prompt_subtext:
            text_lines.append(self._prompt_subtext)
        box_h = pad * 2 + line_h * len(text_lines) + 12
        box_x = margin
        box_y = sh - box_h - margin

        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        surface.blit(bg, (box_x, box_y))

        pygame.draw.line(surface, (255, 255, 255), (box_x, box_y), (box_x + box_w, box_y), 1)

        y = box_y + pad
        main_surf = self.font_large.render(self._prompt_text, True, (255, 255, 255))
        surface.blit(main_surf, (box_x + pad, y))
        y += line_h + 6

        if self._prompt_subtext:
            sub_surf = self.font_small.render(self._prompt_subtext, True, (220, 220, 220))
            surface.blit(sub_surf, (box_x + pad, y))

    def _draw_text(self, surface, text, x, y, font, color):
        text_surf = font.render(text, True, color[:3])
        if len(color) > 3 and color[3] < 255:
            text_surf.set_alpha(color[3])
        surface.blit(text_surf, (x, y))

    def destroy(self):
        if self._texture:
            self._texture.release()
        self.vao.release()
        self.program.release()
