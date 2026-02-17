import pygame
import moderngl
import sys
import glm
from core.camera import Camera
from scene import Cube, GridFloor, LightOrb


class GraphicsEngine:
    def __init__(self, win_size=(1280, 720)):
        pygame.init()

        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

        self.win_size = win_size
        pygame.display.set_mode(win_size, flags=pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption("BigChicken Engine")

        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        # Face culling disabled until winding order is verified
        # self.ctx.enable(moderngl.CULL_FACE)

        # Camera
        self.camera = Camera(position=glm.vec3(0.0, 2.0, 5.0))

        # Mouse capture for FPS-style look
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

        # Lighting
        self.light_pos = glm.vec3(3.0, 5.0, 3.0)
        self.light_color = glm.vec3(1.0, 1.0, 1.0)

        # Scene objects
        self.objects = self._build_scene()

        self.clock = pygame.time.Clock()
        self.time = 0.0

    # ------------------------------------------------------------------
    # Scene setup
    # ------------------------------------------------------------------

    def _build_scene(self):
        """Create the demo scene with a few cubes and a floor."""
        objects = []

        # Floor
        floor = GridFloor(self.ctx, size=10)
        objects.append(floor)

        # Center cube
        cube1 = Cube(self.ctx, color=glm.vec3(0.49, 0.48, 1.0))
        cube1.transform.position = glm.vec3(0.0, 0.5, 0.0)
        objects.append(cube1)

        # Second cube — offset and rotated
        cube2 = Cube(self.ctx, color=glm.vec3(1.0, 0.45, 0.35))
        cube2.transform.position = glm.vec3(3.0, 0.5, -2.0)
        cube2.transform.rotate_euler(yaw_deg=45.0)
        objects.append(cube2)

        # Third cube — small, raised
        cube3 = Cube(self.ctx, color=glm.vec3(0.35, 1.0, 0.55))
        cube3.transform.position = glm.vec3(-2.5, 1.2, 1.0)
        cube3.transform.scale = glm.vec3(0.6)
        objects.append(cube3)

        # Light orb marker
        self.light_orb = LightOrb(self.ctx)
        objects.append(self.light_orb)

        return objects

    # ------------------------------------------------------------------
    # Game loop
    # ------------------------------------------------------------------

    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._quit()
            elif event.type == pygame.MOUSEMOTION:
                dx, dy = event.rel
                self.camera.process_mouse(dx, dy)

    def update(self):
        dt = self.clock.tick(60) / 1000.0
        self.time += dt

        self.camera.process_keyboard(dt)

        # Slowly orbit the light for visual interest
        self.light_pos = glm.vec3(
            glm.cos(self.time * 0.5) * 5.0,
            5.0,
            glm.sin(self.time * 0.5) * 5.0,
        )

        # Move the light orb to the light position
        self.light_orb.transform.position = glm.vec3(self.light_pos)

        for obj in self.objects:
            obj.update(dt)

        # Debug info in title bar
        fps = self.clock.get_fps()
        pos = self.camera.position
        pygame.display.set_caption(
            f"BigChicken Engine | FPS: {fps:.0f} | "
            f"Pos: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
        )

    def render(self):
        self.ctx.clear(0.08, 0.08, 0.12)

        for obj in self.objects:
            obj.set_uniforms(
                self.camera,
                light_pos=self.light_pos,
                light_color=self.light_color,
            )
            obj.render()

        pygame.display.flip()

    def run(self):
        while True:
            self.check_events()
            self.update()
            self.render()

    def _quit(self):
        for obj in self.objects:
            obj.destroy()
        pygame.quit()
        sys.exit()