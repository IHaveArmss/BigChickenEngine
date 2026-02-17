import pygame
import moderngl
import sys
import os
import math
import glm
from core.camera import Camera
from core.texture import TextureLoader
from core.scene_loader import load_scene, save_scene, SceneObject
from core.hud import HUD
from core.editor_ui import EditorUI
from scene import Cube, Triangle, LightOrb, GridFloor

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

        self.win_size = win_size
        pygame.display.set_mode(win_size, flags=pygame.OPENGL | pygame.DOUBLEBUF)
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
        self.move_speed = 2.0
        self.scale_speed = 1.5
        self.cube_counter = 0
        self.tri_counter = 0
        self.light_counter = 0

        # Autosave
        self.autosave_enabled = False
        self.autosave_timer = 0.0
        self.current_scene_file = SCENE_FILE

        # HUD + Editor UI
        self.hud = HUD(self.ctx, win_size)
        self.editor_ui = EditorUI(win_size)
        self.hud.editor_ui = self.editor_ui

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
    # Cursor mode toggle
    # ------------------------------------------------------------------

    def _set_cursor_mode(self, cursor_on):
        self.cursor_mode = cursor_on
        pygame.event.set_grab(not cursor_on)
        pygame.mouse.set_visible(cursor_on)
        if cursor_on:
            pygame.mouse.set_pos(self.win_size[0] // 2, self.win_size[1] // 2)

    # ------------------------------------------------------------------
    # Floor raycasting (Y=0 plane intersect from screen coords)
    # ------------------------------------------------------------------

    def _screen_to_floor(self, screen_x, screen_y):
        """Raycast from screen pixel to Y=0 floor plane. Returns glm.vec3 or None."""
        w, h = self.win_size
        aspect = w / h

        # NDC coords (-1 to 1)
        ndc_x = (2.0 * screen_x / w) - 1.0
        ndc_y = 1.0 - (2.0 * screen_y / h)

        # Inverse projection → view space
        proj = self.camera.projection_matrix(aspect)
        view = self.camera.view_matrix()
        inv_proj = glm.inverse(proj)
        inv_view = glm.inverse(view)

        # Ray in clip space
        ray_clip = glm.vec4(ndc_x, ndc_y, -1.0, 1.0)
        ray_eye = inv_proj * ray_clip
        ray_eye = glm.vec4(ray_eye.x, ray_eye.y, -1.0, 0.0)

        # Ray in world space
        ray_world = glm.vec3(inv_view * ray_eye)
        ray_dir = glm.normalize(ray_world)
        ray_origin = glm.vec3(self.camera.position)

        # Intersect with Y=0 plane
        if abs(ray_dir.y) < 1e-6:
            return None  # Ray parallel to floor
        t = -ray_origin.y / ray_dir.y
        if t < 0:
            return None  # Behind camera
        hit = ray_origin + ray_dir * t
        return hit

    # ------------------------------------------------------------------
    # Object picking
    # ------------------------------------------------------------------

    def _pick_object(self):
        ray_origin = glm.vec3(self.camera.position)
        ray_dir = glm.normalize(glm.vec3(self.camera.front))

        best_t = float('inf')
        best_idx = -1

        for i, obj in enumerate(self.scene_objects):
            center = glm.vec3(obj.position)
            scl = obj.scale
            radius = max(max(scl.x, scl.y, scl.z) * 50.0, 5.0)

            oc = ray_origin - center
            a = glm.dot(ray_dir, ray_dir)
            b = 2.0 * glm.dot(oc, ray_dir)
            c = glm.dot(oc, oc) - radius * radius
            disc = b * b - 4.0 * a * c

            if disc >= 0:
                sqrt_disc = math.sqrt(disc)
                t1 = (-b - sqrt_disc) / (2.0 * a)
                t2 = (-b + sqrt_disc) / (2.0 * a)
                t = t1 if t1 > 0 else t2
                if t > 0 and t < best_t:
                    best_t = t
                    best_idx = i

        return best_idx

    def _pick_object_from_screen(self, screen_x, screen_y):
        """Pick object via screen-space ray (for cursor mode)."""
        w, h = self.win_size
        aspect = w / h
        ndc_x = (2.0 * screen_x / w) - 1.0
        ndc_y = 1.0 - (2.0 * screen_y / h)

        proj = self.camera.projection_matrix(aspect)
        view = self.camera.view_matrix()
        inv_proj = glm.inverse(proj)
        inv_view = glm.inverse(view)

        ray_clip = glm.vec4(ndc_x, ndc_y, -1.0, 1.0)
        ray_eye = inv_proj * ray_clip
        ray_eye = glm.vec4(ray_eye.x, ray_eye.y, -1.0, 0.0)
        ray_world = glm.vec3(inv_view * ray_eye)
        ray_dir = glm.normalize(ray_world)
        ray_origin = glm.vec3(self.camera.position)

        best_t = float('inf')
        best_idx = -1

        for i, obj in enumerate(self.scene_objects):
            center = glm.vec3(obj.position)
            scl = obj.scale
            radius = max(max(scl.x, scl.y, scl.z) * 50.0, 5.0)

            oc = ray_origin - center
            a = glm.dot(ray_dir, ray_dir)
            b_val = 2.0 * glm.dot(oc, ray_dir)
            c_val = glm.dot(oc, oc) - radius * radius
            disc = b_val * b_val - 4.0 * a * c_val

            if disc >= 0:
                sqrt_disc = math.sqrt(disc)
                t1 = (-b_val - sqrt_disc) / (2.0 * a)
                t2 = (-b_val + sqrt_disc) / (2.0 * a)
                t = t1 if t1 > 0 else t2
                if t > 0 and t < best_t:
                    best_t = t
                    best_idx = i

        return best_idx

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    def _spawn_at(self, obj_type, position):
        """Spawn an object at a specific world position."""
        if obj_type == 'cube':
            self.cube_counter += 1
            name = f"cube_{self.cube_counter}"
            mesh = Cube(self.ctx, color=glm.vec3(0.49, 0.48, 1.0))
            fmt = 'cube'
        elif obj_type == 'triangle':
            self.tri_counter += 1
            name = f"tri_{self.tri_counter}"
            mesh = Triangle(self.ctx, color=glm.vec3(1.0, 0.4, 0.2))
            fmt = 'triangle'
        elif obj_type == 'light':
            self.light_counter += 1
            name = f"light_{self.light_counter}"
            mesh = LightOrb(self.ctx, radius=0.3, color=glm.vec3(1.0, 1.0, 0.9))
            fmt = 'light'
        else:
            return

        # Place at the position, with Y offset so it sits on floor
        spawn_pos = glm.vec3(position.x, position.y + 0.5, position.z)
        mesh.transform.position = glm.vec3(spawn_pos)
        mesh.transform.scale = glm.vec3(1.0)

        is_light = (obj_type == 'light')
        obj = SceneObject(name, '', fmt, [mesh], is_light=is_light)
        self.scene_objects.append(obj)
        self._rebuild_renderables()

        self.selected_index = len(self.scene_objects) - 1
        self.editor_ui._current_obj_name = None
        print(f"[DevMode] Placed {obj_type} '{name}' at ({spawn_pos.x:.1f}, {spawn_pos.y:.1f}, {spawn_pos.z:.1f})")

    def _spawn_in_front(self, obj_type):
        """Fallback: spawn 5 units in front of camera."""
        pos = self.camera.position + self.camera.front * 5.0
        self._spawn_at(obj_type, pos)

    def _delete_selected(self):
        if self.selected_index < 0:
            return
        obj = self.scene_objects[self.selected_index]
        print(f"[DevMode] Deleted '{obj.name}'")
        for m in obj.meshes:
            m.destroy()
        self.scene_objects.pop(self.selected_index)
        self.selected_index = -1
        self.editor_ui._current_obj_name = None
        self._rebuild_renderables()

    # ------------------------------------------------------------------
    # Save As
    # ------------------------------------------------------------------

    def _save_as(self, filename):
        """Save scene to scenes/<filename>.json"""
        safe_name = "".join(c for c in filename if c.isalnum() or c in ('_', '-'))
        if not safe_name:
            safe_name = "untitled"
        path = os.path.join('scenes', f'{safe_name}.json')
        os.makedirs('scenes', exist_ok=True)
        save_scene(path, self.scene_objects)
        self.current_scene_file = path
        print(f"[DevMode] Scene saved as: {path}")

    # ------------------------------------------------------------------
    # Apply UI property edits
    # ------------------------------------------------------------------

    def _apply_ui_properties(self):
        if self.selected_index < 0 or self.selected_index >= len(self.scene_objects):
            return
        obj = self.scene_objects[self.selected_index]
        # Only apply if the UI is actually showing THIS object's properties
        if self.editor_ui._current_obj_name != obj.name:
            return
        values = self.editor_ui.read_property_values()

        try:
            px = float(values.get('pos_x', obj.position.x))
            py = float(values.get('pos_y', obj.position.y))
            pz = float(values.get('pos_z', obj.position.z))
            obj.position = glm.vec3(px, py, pz)
        except (ValueError, TypeError):
            pass

        try:
            sx = float(values.get('scl_x', obj.scale.x))
            sy = float(values.get('scl_y', obj.scale.y))
            sz = float(values.get('scl_z', obj.scale.z))
            obj.scale = glm.vec3(sx, sy, sz)
        except (ValueError, TypeError):
            pass

        hex_val = values.get('color', '')
        if hex_val:
            rgb = EditorUI._parse_hex(hex_val)
            if rgb and obj.meshes:
                color = glm.vec3(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
                for m in obj.meshes:
                    if hasattr(m, 'color'):
                        m.color = color
                if obj.is_light:
                    obj.light_color = color

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def check_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            elif event.type == pygame.KEYDOWN:
                if self.editor_ui.has_active_input():
                    self.editor_ui.handle_event(event, pygame.mouse.get_pos())
                    continue

                if event.key == pygame.K_ESCAPE:
                    if self.cursor_mode:
                        self._set_cursor_mode(False)
                        self.editor_ui.placement_mode = None
                    else:
                        self._quit()

                elif event.key == pygame.K_F1:
                    self.dev_mode = not self.dev_mode
                    self.hud.dev_mode = self.dev_mode
                    self.editor_ui.visible = self.dev_mode
                    if self.dev_mode:
                        self._set_cursor_mode(True)
                        print(f"\n[DevMode] ON — cursor mode")
                    else:
                        self._set_cursor_mode(False)
                        self.editor_ui.visible = False
                        self.editor_ui.placement_mode = None
                        print("[DevMode] OFF")

                elif event.key == pygame.K_F2:
                    self._set_cursor_mode(not self.cursor_mode)
                    if not self.cursor_mode:
                        self.editor_ui.placement_mode = None

                elif event.key == pygame.K_h:
                    self.hud.toggle_controls()

                elif event.key == pygame.K_TAB and self.dev_mode:
                    self._print_scene_info()
                    save_scene(self.current_scene_file, self.scene_objects)

                elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    if self.dev_mode:
                        save_scene(self.current_scene_file, self.scene_objects)

                elif event.key == pygame.K_c and self.dev_mode and not self.cursor_mode:
                    self._spawn_in_front('cube')

                elif event.key == pygame.K_DELETE and self.dev_mode:
                    self._delete_selected()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.cursor_mode:
                    mouse_pos = pygame.mouse.get_pos()

                    if self.editor_ui.is_point_on_panel(mouse_pos):
                        action = self.editor_ui.handle_event(event, mouse_pos)
                        if action:
                            if action['action'] == 'save_as':
                                self._save_as(action['filename'])
                            elif action['action'] == 'autosave_toggle':
                                self.autosave_enabled = action['enabled']
                                self.autosave_timer = 0.0
                                status = "ON" if self.autosave_enabled else "OFF"
                                print(f"[DevMode] Autosave: {status}")
                    else:
                        # Click in viewport
                        if self.editor_ui.placement_mode:
                            # Place object where ray hits floor
                            floor_hit = self._screen_to_floor(*mouse_pos)
                            if floor_hit:
                                self._spawn_at(self.editor_ui.placement_mode, floor_hit)
                            else:
                                # Fallback if looking away from floor
                                self._spawn_in_front(self.editor_ui.placement_mode)
                            self.editor_ui.placement_mode = None
                        elif self.dev_mode:
                            idx = self._pick_object_from_screen(*mouse_pos)
                            if idx >= 0:
                                self.selected_index = idx
                                self.editor_ui._current_obj_name = None
                                print(f"[DevMode] Selected: '{self.scene_objects[idx].name}'")
                            elif self.selected_index >= 0:
                                self.selected_index = -1
                                self.editor_ui._current_obj_name = None
                                print("[DevMode] Deselected")

                elif self.dev_mode and event.button == 1:
                    idx = self._pick_object()
                    if idx >= 0:
                        self.selected_index = idx
                        self.editor_ui._current_obj_name = None
                        print(f"[DevMode] Selected: '{self.scene_objects[idx].name}'")
                    elif self.selected_index >= 0:
                        self.selected_index = -1
                        self.editor_ui._current_obj_name = None
                        print("[DevMode] Deselected")

            elif event.type == pygame.MOUSEMOTION:
                if not self.cursor_mode:
                    dx, dy = event.rel
                    self.camera.process_mouse(dx, dy)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self):
        dt = self.clock.tick(60) / 1000.0
        self.time += dt

        if not self.cursor_mode:
            self.camera.process_keyboard(dt)

        if self.dev_mode and self.selected_index >= 0 and not self.cursor_mode:
            self._handle_dev_keys(dt)

        if self.cursor_mode and self.dev_mode:
            self._apply_ui_properties()

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
        pos = self.camera.position
        title = f"BigChicken | FPS: {fps:.0f}"
        if self.dev_mode:
            mode = "CURSOR" if self.cursor_mode else "FPS"
            title += f" | DEV [{mode}]"
            if self.autosave_enabled:
                title += " | AUTOSAVE"
        pygame.display.set_caption(title)

    def _handle_dev_keys(self, dt):
        keys = pygame.key.get_pressed()
        obj = self.scene_objects[self.selected_index]
        pos = glm.vec3(obj.position)
        scl = glm.vec3(obj.scale)
        move = self.move_speed * dt

        if keys[pygame.K_UP]:    pos.z -= move
        if keys[pygame.K_DOWN]:  pos.z += move
        if keys[pygame.K_LEFT]:  pos.x -= move
        if keys[pygame.K_RIGHT]: pos.x += move
        if keys[pygame.K_q]:     pos.y -= move
        if keys[pygame.K_e]:     pos.y += move

        scaling_up = keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]
        scaling_down = keys[pygame.K_MINUS]
        if scaling_up or scaling_down:
            factor = (1.0 + self.scale_speed * dt) if scaling_up else max(1.0 - self.scale_speed * dt, 0.01)
            if keys[pygame.K_1]:     scl.x *= factor
            elif keys[pygame.K_2]:   scl.y *= factor
            elif keys[pygame.K_3]:   scl.z *= factor
            else:                    scl *= factor

        obj.position = pos
        obj.scale = scl

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self):
        self.ctx.clear(0.08, 0.08, 0.12)

        scene_lights = [(self.light_pos, self.light_color)]
        for obj in self.scene_objects:
            if obj.is_light:
                scene_lights.append((
                    glm.vec3(obj.position),
                    obj.light_color * obj.light_intensity
                ))

        primary_lp = scene_lights[0][0]
        primary_lc = scene_lights[0][1]

        for obj in self.all_renderables:
            obj.set_uniforms(self.camera, light_pos=primary_lp, light_color=primary_lc)
            obj.render()

        # Wireframe highlight
        if self.dev_mode and 0 <= self.selected_index < len(self.scene_objects):
            sel = self.scene_objects[self.selected_index]
            self.ctx.wireframe = True
            for mesh in sel.meshes:
                mesh.set_uniforms(
                    self.camera, light_pos=primary_lp,
                    light_color=glm.vec3(1.0), object_color=glm.vec3(0.0, 1.0, 0.4),
                )
                mesh.render()
            self.ctx.wireframe = False

        self.hud.render()
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _print_scene_info(self):
        print("\n" + "=" * 60)
        print(f"  SCENE: {self.current_scene_file}")
        print(f"  Objects: {len(self.scene_objects)}")
        print("=" * 60)
        for i, obj in enumerate(self.scene_objects):
            p = obj.position
            s = obj.scale
            sel = " [SELECTED]" if i == self.selected_index else ""
            kind = " (light)" if obj.is_light else ""
            print(f"  [{i}] {obj.name} ({obj.format}){kind}{sel}")
            if obj.model_path:
                print(f"      Model:    {obj.model_path}")
            print(f"      Position: ({p.x:.2f}, {p.y:.2f}, {p.z:.2f})")
            print(f"      Scale:    ({s.x:.4f}, {s.y:.4f}, {s.z:.4f})")
        print("=" * 60 + "\n")

    def run(self):
        while True:
            self.check_events()
            self.update()
            self.render()

    def _quit(self):
        for obj in self.all_renderables:
            obj.destroy()
        self.texture_loader.destroy()
        self.hud.destroy()
        pygame.quit()
        sys.exit()