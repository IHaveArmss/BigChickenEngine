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
        self.font_large = pygame.font.SysFont('Consolas', 20, bold=True)
        self.font_small = pygame.font.SysFont('Consolas', 16)

        # HUD texture (recreated each frame)
        self._texture = None

        # State
        self.show_controls = False
        self.dev_mode = False
        self.selected_name = ""
        self.selected_pos = None
        self.selected_scale = None
        self.stretch_axis = None
        self.editor_ui = None  # set by engine after creation

    def toggle_controls(self):
        self.show_controls = not self.show_controls

    def render(self):
        """Render the HUD overlay on top of the scene."""
        surface = self._build_surface()
        if surface is None:
            return

        data = pygame.image.tostring(surface, 'RGBA', True)
        w, h = surface.get_size()

        if self._texture:
            self._texture.release()
        self._texture = self.ctx.texture((w, h), 4, data)
        self._texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

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
        # Always draw crosshair, rest only in dev mode
        surface = pygame.Surface(self.win_size, pygame.SRCALPHA)

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

        if not self.dev_mode and not self.show_controls:
            return surface

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

        return surface

    def _draw_controls_panel(self, surface):
        """Draw the controls help panel."""
        panel_w, panel_h = 380, 370
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
                ("Escape", "Quit"),
            ]),
            ("Dev Mode", [
                ("F1", "Toggle dev mode"),
                ("H", "Toggle this panel"),
                ("Click", "Select object"),
                ("+ / -", "Scale (uniform)"),
                ("1/2/3 + scale", "Stretch X / Y / Z"),
                ("Arrows", "Move object XZ"),
                ("Q / E", "Move object Y"),
                ("C", "Spawn cube at crosshair"),
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
