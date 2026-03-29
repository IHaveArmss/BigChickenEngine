"""Main Menu — displays assets/mainmenu.png fullscreen with a Start button.

Uses the same ModernGL screen-quad pipeline as VideoPlayer so it works
cleanly inside the OpenGL context without touching the 3D scene.
The Pygame overlay (Start button) is composited on top as a separate texture.
"""

import os
import pygame
import moderngl


class MainMenu:
    """Full-screen main menu rendered via ModernGL + Pygame HUD overlay."""

    def __init__(self, ctx, shader_cache, image_path):
        self.ctx = ctx
        self.shader_cache = shader_cache
        self.image_path = image_path
        self.valid = False

        if not os.path.exists(image_path):
            print(f"[MainMenu] ERROR: Image not found: {image_path}")
            return

        # ── Background image texture ────────────────────────────────────────
        img = pygame.image.load(image_path).convert_alpha()
        self._img_orig = img           # keep original for scaling
        self._bg_texture = None        # created lazily on first render
        self._bg_size = (0, 0)

        # ── Screen-quad shader (shared with VideoPlayer / HUD) ───────────────
        self.program = shader_cache.get('screen')
        self.vao = ctx.vertex_array(self.program, [])

        # ── Overlay shader (same program — we re-use it for the HUD surface) ─
        self._hud_texture = None
        self._hud_size = (0, 0)

        # ── Fonts ────────────────────────────────────────────────────────────
        pygame.font.init()
        try:
            self._font_title  = pygame.font.SysFont('Segoe UI', 56, bold=True)
            self._font_button = pygame.font.SysFont('Segoe UI', 36, bold=True)
        except Exception:
            self._font_title  = pygame.font.SysFont(None, 56, bold=True)
            self._font_button = pygame.font.SysFont(None, 36, bold=True)

        self.valid = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self):
        """Block until the player clicks Start (or presses Enter / Space)."""
        if not self.valid:
            print("[MainMenu] Skipping — menu is not valid.")
            return

        clock = pygame.time.Clock()
        running = True
        anim_time = 0.0          # drives button pulse animation

        print("[MainMenu] Showing main menu…")

        while running:
            dt = clock.tick(60) / 1000.0
            anim_time += dt

            # ── Events ──────────────────────────────────────────────────────
            mouse_pos = pygame.mouse.get_pos()
            win_size  = pygame.display.get_surface().get_size()

            btn_rect  = self._button_rect(win_size)
            hovered   = btn_rect.collidepoint(mouse_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys; sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and hovered:
                        running = False

            if not running:
                break

            # ── Render background ────────────────────────────────────────────
            self._render_background(win_size)

            # ── Render HUD overlay (Start button) ────────────────────────────
            self._render_hud(win_size, btn_rect, hovered, anim_time)

            pygame.display.flip()

        print("[MainMenu] Start pressed — entering game.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _button_rect(self, win_size):
        """Return the rect for the Start button (bottom-centre of screen)."""
        w, h = win_size
        btn_w, btn_h = 260, 64
        btn_x = (w - btn_w) // 2
        btn_y = int(h * 0.82)          # ~82 % down the screen
        return pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    def _render_background(self, win_size):
        """Upload the background image as a ModernGL texture and draw it."""
        if self._bg_texture is None or win_size != self._bg_size:
            if self._bg_texture:
                self._bg_texture.release()
            scaled = pygame.transform.smoothscale(self._img_orig, win_size)
            # OpenGL expects bottom-left origin → flip vertically
            flipped = pygame.transform.flip(scaled, False, True)
            data = pygame.image.tostring(flipped, 'RGB')
            self._bg_texture = self.ctx.texture(win_size, 3, data)
            self._bg_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._bg_size = win_size

        self.ctx.screen.use()
        self.ctx.clear(0.0, 0.0, 0.0)
        self.ctx.disable(moderngl.DEPTH_TEST)

        self._bg_texture.use(location=0)
        if 'u_texture' in self.program:
            self.program['u_texture'].value = 0
        self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def _render_hud(self, win_size, btn_rect, hovered, anim_time):
        """Build Pygame surface with Start button, upload as texture, blend on top."""
        import math

        surf = pygame.Surface(win_size, pygame.SRCALPHA)

        # ── Animated start button ────────────────────────────────────────────
        pulse = 0.5 + 0.5 * math.sin(anim_time * 3.0)   # 0..1

        if hovered:
            bg_color  = (255, 220, 50, 230)
            txt_color = (30, 20, 0)
            border_c  = (255, 255, 255, 255)
        else:
            r = int(30  + pulse * 20)
            g = int(180 + pulse * 40)
            b = int(100 + pulse * 60)
            bg_color  = (r, g, b, 200)
            txt_color = (255, 255, 255)
            border_c  = (255, 255, 255, int(150 + pulse * 100))

        # Shadow
        shadow_rect = btn_rect.move(4, 6)
        shadow_surf = pygame.Surface((shadow_rect.w, shadow_rect.h), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 100))
        surf.blit(shadow_surf, shadow_rect.topleft)

        # Button background
        btn_surf = pygame.Surface((btn_rect.w, btn_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, bg_color, btn_surf.get_rect(), border_radius=16)
        pygame.draw.rect(btn_surf, border_c, btn_surf.get_rect(), width=2, border_radius=16)
        surf.blit(btn_surf, btn_rect.topleft)

        # Button label
        label = self._font_button.render("START", True, txt_color)
        lx = btn_rect.x + (btn_rect.w - label.get_width()) // 2
        ly = btn_rect.y + (btn_rect.h - label.get_height()) // 2
        surf.blit(label, (lx, ly))

        # ── Sub-hint text ────────────────────────────────────────────────────
        hint_font = pygame.font.SysFont('Segoe UI', 20)
        hint = hint_font.render("or press  SPACE / ENTER", True, (220, 220, 220, 180))
        hint.set_alpha(160)
        hx = (win_size[0] - hint.get_width()) // 2
        hy = btn_rect.bottom + 14
        surf.blit(hint, (hx, hy))

        # ── Upload as ModernGL texture and draw with blending ────────────────
        # Flip for OpenGL coordinate system
        flipped = pygame.transform.flip(surf, False, True)
        data = pygame.image.tostring(flipped, 'RGBA')
        w, h = win_size

        if self._hud_texture is None or (w, h) != self._hud_size:
            if self._hud_texture:
                self._hud_texture.release()
            self._hud_texture = self.ctx.texture((w, h), 4, data)
            self._hud_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self._hud_size = (w, h)
        else:
            self._hud_texture.write(data)

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self._hud_texture.use(location=0)
        if 'u_texture' in self.program:
            self.program['u_texture'].value = 0
        self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

        self.ctx.disable(moderngl.BLEND)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def destroy(self):
        if self._bg_texture:
            self._bg_texture.release()
        if self._hud_texture:
            self._hud_texture.release()
        if self.vao:
            self.vao.release()
