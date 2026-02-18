import pygame
import moderngl
import sys
import os
import glm
from core.camera import Camera
from core.texture import TextureLoader
from core.scene_loader import load_scene, save_scene
from core.hud import HUD
from core.editor_ui import EditorUI
from core.input_handler import InputHandler
from core.renderer import Renderer
from core.dev_mode import DevMode
from core.scene_hierarchy import SceneHierarchy
from core.obj_exporter import export_folder_to_obj
from scene import LightOrb, GridFloor

# ======================================================================
SCENE_FILE = 'scenes/demo.json'
# ======================================================================

AUTOSAVE_INTERVAL = 30.0  # seconds


class GraphicsEngine:
    def __init__(self, win_size=(1280, 720)):
        pygame.init()

        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

        # Start with a large decorated window (has X button, title bar)
        display_info = pygame.display.Info()
        self.win_size = (display_info.current_w - 100, display_info.current_h - 100)
        pygame.display.set_mode(
            self.win_size,
            flags=pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE,
        )
        pygame.display.set_caption("BigChicken Engine")

        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST)

        self.camera = Camera(position=glm.vec3(0.0, 5.0, 15.0))
        self.camera.far = 500.0

        self.cursor_mode = False
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

        self.light_pos = glm.vec3(5.0, 10.0, 5.0)
        self.light_color = glm.vec3(1.0, 1.0, 1.0)

        self.texture_loader = TextureLoader(self.ctx)

        # Dev mode
        self.dev_mode = False
        self.selected_index = -1

        # Autosave
        self.autosave_enabled = False
        self.autosave_timer = 0.0
        self.current_scene_file = SCENE_FILE

        # Subsystems
        self.hud = HUD(self.ctx, self.win_size)
        self.editor_ui = EditorUI(self.win_size)
        self.hud.editor_ui = self.editor_ui
        self.scene_hierarchy = SceneHierarchy(self.win_size)
        self.hud.scene_hierarchy = self.scene_hierarchy
        self.input_handler = InputHandler(self)
        self.renderer = Renderer(self.ctx)
        self.dev_tools = DevMode()

        self._build_scene()

        self.clock = pygame.time.Clock()
        self.time = 0.0

    # ------------------------------------------------------------------
    # Scene
    # ------------------------------------------------------------------

    def _build_scene(self):
        self.static_objects = []
        floor = GridFloor(self.ctx, size=50)
        self.static_objects.append(floor)

        self.light_orb = LightOrb(self.ctx)
        self.static_objects.append(self.light_orb)

        self.scene_objects, self.model_meshes = load_scene(
            self.current_scene_file, self.ctx, self.texture_loader
        )
        self._rebuild_renderables()

    def _rebuild_renderables(self):
        self.all_renderables = list(self.static_objects)
        for obj in self.scene_objects:
            self.all_renderables.extend(obj.meshes)

    # ------------------------------------------------------------------
    # Save As
    # ------------------------------------------------------------------

    def _save_as(self, filename):
        safe_name = "".join(c for c in filename if c.isalnum() or c in ('_', '-'))
        if not safe_name:
            safe_name = "untitled"
        path = os.path.join('scenes', f'{safe_name}.json')
        os.makedirs('scenes', exist_ok=True)
        save_scene(path, self.scene_objects)
        self.current_scene_file = path
        print(f"[DevMode] Scene saved as: {path}")

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self):
        dt = self.clock.tick(60) / 1000.0
        self.time += dt

        if not self.cursor_mode:
            self.camera.process_keyboard(dt)

        if self.dev_mode and self.selected_index >= 0 and not self.cursor_mode:
            self.dev_tools.handle_movement_keys(dt, self.scene_objects, self.selected_index)

        if self.cursor_mode and self.dev_mode:
            self.dev_tools.apply_ui_properties(
                self.scene_objects, self.selected_index, self.editor_ui
            )

        # Autosave
        if self.autosave_enabled and self.dev_mode:
            self.autosave_timer += dt
            if self.autosave_timer >= AUTOSAVE_INTERVAL:
                self.autosave_timer = 0.0
                save_scene(self.current_scene_file, self.scene_objects)
                print("[Autosave] Scene saved")

        # Update editor UI
        sel_obj = None
        if 0 <= self.selected_index < len(self.scene_objects):
            sel_obj = self.scene_objects[self.selected_index]
        self.editor_ui.update(dt, pygame.mouse.get_pos(), sel_obj)
        if sel_obj:
            self.editor_ui.refresh_values(sel_obj)

        # Update hierarchy panel
        self.scene_hierarchy.update(pygame.mouse.get_pos(), self.scene_objects)

        # Orbit light
        self.light_pos = glm.vec3(
            glm.cos(self.time * 0.3) * 15.0, 10.0,
            glm.sin(self.time * 0.3) * 15.0,
        )
        self.light_orb.transform.position = glm.vec3(self.light_pos)

        for obj in self.all_renderables:
            obj.update(dt)

        # HUD info
        if sel_obj:
            self.hud.selected_name = sel_obj.name
            self.hud.selected_pos = sel_obj.position
            self.hud.selected_scale = sel_obj.scale
        else:
            self.hud.selected_name = ""
            self.hud.selected_pos = None
            self.hud.selected_scale = None

        # Pass scene data to HUD for hierarchy panel
        self.hud.scene_objects_ref = self.scene_objects
        self.hud._selected_index = self.selected_index

        # Check for pending export requests
        export_folder = self.scene_hierarchy.pop_export_request()
        if export_folder:
            export_folder_to_obj(export_folder, self.scene_objects)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_1]:
            self.hud.stretch_axis = 'X'
        elif keys[pygame.K_2]:
            self.hud.stretch_axis = 'Y'
        elif keys[pygame.K_3]:
            self.hud.stretch_axis = 'Z'
        else:
            self.hud.stretch_axis = None

        fps = self.clock.get_fps()
        title = f"BigChicken | FPS: {fps:.0f}"
        if self.dev_mode:
            mode = "CURSOR" if self.cursor_mode else "FPS"
            title += f" | DEV [{mode}]"
            if self.autosave_enabled:
                title += " | AUTOSAVE"
        pygame.display.set_caption(title)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self):
        self.renderer.render(
            self.all_renderables, self.scene_objects, self.camera, self.hud,
            self.light_pos, self.light_color,
            self.dev_mode, self.selected_index,
        )
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        while True:
            self.input_handler.process_events()
            self.update()
            self.render()

    def _quit(self):
        for obj in self.all_renderables:
            obj.destroy()
        self.texture_loader.destroy()
        self.hud.destroy()
        pygame.quit()
        sys.exit()