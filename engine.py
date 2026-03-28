import pygame
import moderngl
import sys
import os
import json
import glm
import math
import traceback
from core.camera import Camera
from core.texture import TextureLoader
from core.scene_loader import load_scene, save_scene, spawn_from_entry, SceneObject
from core.hud import HUD
from core.editor_ui import EditorUI
from core.input_handler import InputHandler
from core.renderer import Renderer
from core.dev_mode import DevMode
from core.scene_hierarchy import SceneHierarchy
from core.obj_exporter import export_folder_to_obj
from scene import LightOrb
from core.physics_system import PhysicsSystem, FIXED_TIMESTEP
from core.script_manager import ScriptManager
from core.interaction_manager import InteractionManager
from core.dialogue_manager import DialogueManager
from core.audio_manager import AudioManager
from core.cutscene_manager import CutsceneManager
from core.prefab_manager import save_prefab, load_prefab, list_prefabs
from core.render_settings import RenderSettings
from core.serialization import serialize_scene_object
from core.resource_manager import ResourceManager


class ShaderCache:
    """Engine-level shader cache to avoid recompiling shaders per-object."""
    
    def __init__(self, ctx):
        self.ctx = ctx
        self._programs = {}
    
    def get(self, name):
        if name not in self._programs:
            try:
                with open(f'shaders/{name}.vert') as f:
                    vs = f.read()
                with open(f'shaders/{name}.frag') as f:
                    fs = f.read()
                self._programs[name] = self.ctx.program(vertex_shader=vs, fragment_shader=fs)
            except Exception as e:
                print(f"\n[ShaderCache] ERROR: Failed to compile shader '{name}':")
                print(e)
                # Try to return a fallback so the engine doesn't just crash
                if name != 'phong':
                    return self.get('phong')
                return None
        return self._programs.get(name)
    
    def get_skinned(self):
        if 'phong_skinned' not in self._programs:
            with open('shaders/phong_skinned.vert') as f:
                vs = f.read()
            with open('shaders/phong.frag') as f:
                fs = f.read()
            self._programs['phong_skinned'] = self.ctx.program(vertex_shader=vs, fragment_shader=fs)
        return self._programs['phong_skinned']
    
    def clear(self):
        self._programs.clear()


# ======================================================================
SCENE_FILE = 'scenes/cutscene_demo.json'
PLAY_INTRO = False # Set to False to skip the opening video
# ======================================================================

AUTOSAVE_INTERVAL = 30.0  # seconds
UNDO_HISTORY_LIMIT = 100


class GraphicsEngine:
    def _serialize_object_entry(self, obj):
        return serialize_scene_object(obj)

    def _capture_scene_state(self):
        return {
            'scene_file': self.current_scene_file,
            'settings': self._build_scene_settings(),
            'objects': [self._serialize_object_entry(o) for o in self.scene_objects],
            'selected_index': self.selected_index,
        }

    def _restore_scene_state(self, state):
        self.script_manager.stop_all()
        self.physics_system.reset()
        for obj in self.scene_objects:
            for m in obj.meshes:
                m.destroy()
        self.scene_objects.clear()
        self.model_meshes = []
        self._pending_spawns.clear()
        self._pending_destroys.clear()

        self.current_scene_file = state.get('scene_file', self.current_scene_file)
        self._apply_scene_settings(state.get('settings', {}))

        for entry in state.get('objects', []):
            obj = spawn_from_entry(entry, self.ctx, self.texture_loader, self.shader_cache)
            if obj is not None:
                self.scene_objects.append(obj)
        self.selected_index = min(state.get('selected_index', -1), len(self.scene_objects) - 1)
        self._rebuild_renderables()
        self.editor_ui._current_obj_name = None
        self.editor_ui.set_scene_context(self.current_scene_file, self.list_scene_files())
        self.editor_ui.set_prefab_context(self.list_prefab_names())
        self.editor_ui.available_cutscenes = self.cutscenes.list_cutscenes()

    def _record_history_snapshot(self, force=False):
        if self._history_suspend:
            return
        if not force and self._skip_snapshot_frames > 0:
            self._skip_snapshot_frames -= 1
            return
        if force:
            self._skip_snapshot_frames = 0  # Clear skip on explicit snapshot (load/save)
        if not self.dev_mode and not force:
            return
        snapshot = self._capture_scene_state()
        signature = json.dumps(snapshot, sort_keys=True)
        if force or signature != self._history_last_signature:
            self._undo_stack.append(snapshot)
            if len(self._undo_stack) > UNDO_HISTORY_LIMIT:
                self._undo_stack.pop(0)
            self._history_last_signature = signature
            if not self._history_replaying:
                self._redo_stack.clear()

    def undo(self):
        if len(self._undo_stack) <= 1:
            print("[History] Nothing to undo")
            return
        self._history_replaying = True
        current = self._undo_stack.pop()
        self._redo_stack.append(current)
        target = self._undo_stack[-1]
        self._history_suspend = True
        self._restore_scene_state(target)
        self._history_suspend = False
        self._history_last_signature = json.dumps(target, sort_keys=True)
        self._history_replaying = False
        self._skip_snapshot_frames = 2  # Skip next 2 frames so redo stack isn't cleared
        print("[History] Undo")

    def redo(self):
        if not self._redo_stack:
            print("[History] Nothing to redo")
            return
        self._history_replaying = True
        target = self._redo_stack.pop()
        self._history_suspend = True
        self._restore_scene_state(target)
        self._history_suspend = False
        self._undo_stack.append(target)
        self._history_last_signature = json.dumps(target, sort_keys=True)
        self._history_replaying = False
        self._skip_snapshot_frames = 2  # Skip next 2 frames so redo stack isn't cleared
        print("[History] Redo")

    def list_scene_files(self):
        """Return scene JSON paths under scenes/."""
        scene_dir = 'scenes'
        if not os.path.isdir(scene_dir):
            return []
        files = []
        for name in os.listdir(scene_dir):
            if name.lower().endswith('.json'):
                files.append(os.path.join(scene_dir, name).replace('\\', '/'))
        return sorted(files)

    def list_prefab_names(self):
        return sorted(list_prefabs())

    def toggle_dev_mode(self):
        self.dev_mode = not self.dev_mode
        # Dev mode always starts in cursor mode (UI visible, mouse free).
        # Play mode always starts with mouse locked to window.
        self.cursor_mode = self.dev_mode
        pygame.mouse.set_visible(self.cursor_mode)
        pygame.event.set_grab(not self.cursor_mode)

        if self.dev_mode:
            # Entered Editor Mode — stop scripts and restore pre-play transforms
            self.interaction_manager.clear()
            self.dialogue.active = False
            self.script_manager.stop_all()
            self.physics_system.reset()
            if self._saved_transforms:
                for obj in self.scene_objects:
                    saved = self._saved_transforms.get(id(obj))
                    if saved:
                        obj.position = saved['position']
                        obj.set_rotation_euler(*saved['rotation_euler'])
                        obj.scale = saved['scale']
                self._saved_transforms.clear()
        else:
            # Entered Play Mode — flush any pending UI edits so scripts are up-to-date
            self.dev_tools.apply_ui_properties(
                self.scene_objects, self.selected_index, self.editor_ui
            )

            # Snapshot transforms so we can restore later
            self._saved_transforms = {}
            for obj in self.scene_objects:
                euler = obj.rotation_euler
                self._saved_transforms[id(obj)] = {
                    'position': glm.vec3(obj.position),
                    'rotation_euler': (euler.x, euler.y, euler.z),
                    'scale': glm.vec3(obj.scale),
                }
            self.play_camera = None
            self.script_manager.load_scripts(self, self.scene_objects)
    def __init__(self, win_size=(1280, 720)):
        self.play_intro_enabled = True
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

        self.shader_cache = ShaderCache(self.ctx)

        self.editor_camera = Camera(position=glm.vec3(0.0, 5.0, 15.0))
        self.editor_camera.far = 500.0
        
        self.play_camera = None

        self.cursor_mode = False
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)

        # Global state for dialogue system and game logic
        self.global_flags = {}

        self.light_pos = glm.vec3(5.0, 10.0, 5.0)
        self.light_color = glm.vec3(1.0, 1.0, 1.0)
        self.main_light_dir = glm.normalize(glm.vec3(-0.5, -1.0, -0.3))

        self.texture_loader = TextureLoader(self.ctx)
        self.render_settings = RenderSettings()

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
        self.renderer._init_skybox(self.texture_loader)
        self.dev_tools = DevMode()
        self.physics_system = PhysicsSystem()
        self.script_manager = ScriptManager()
        self.interaction_manager = InteractionManager(self)
        self.dialogue = DialogueManager(self)
        self.hud.dialogue_manager = self.dialogue
        self.audio = AudioManager()
        self.resource_manager = ResourceManager(self.ctx, self.texture_loader)
        
        # Hyper-Load: Pre-load assets from all scenes to ensure smooth transitions
        scene_files = self.list_scene_files()
        self.resource_manager.pre_load_scenes(scene_files)

        self.cutscenes = CutsceneManager(self)
        self.editor_ui.available_cutscenes = self.cutscenes.list_cutscenes()

        # Keep Dev UI in sync with runtime settings (initial defaults)
        self.editor_ui.play_intro_enabled = self.play_intro_enabled
        self.editor_ui.ps2_enabled = self.render_settings.ps2_enabled
        self.editor_ui.postprocess_enabled = self.render_settings.postprocess_enabled
        self.editor_ui.quantize_enabled = self.render_settings.quantize_enabled
        self.editor_ui.dither_enabled = self.render_settings.dither_enabled
        self.editor_ui.lighting_ramp_enabled = self.render_settings.lighting_ramp_enabled
        self.editor_ui.specular_banding_enabled = self.render_settings.specular_banding_enabled
        self.editor_ui.wobble_enabled = self.render_settings.wobble_enabled
        self.editor_ui.pixel_size_input.text = str(self.render_settings.pixel_size)
        self.editor_ui.quantize_steps_input.text = str(self.render_settings.quantize_steps)
        self.editor_ui.lighting_ramp_steps_input.text = str(self.render_settings.lighting_ramp_steps)
        self.editor_ui.specular_steps_input.text = str(self.render_settings.specular_steps)
        self.editor_ui.wobble_pixel_input.text = str(self.render_settings.wobble_pixel_size)
        self.editor_ui.directional_shadows_enabled = self.render_settings.directional_shadows_enabled
        self.editor_ui.directional_shadow_resolution_input.text = str(self.render_settings.directional_shadow_resolution)
        self.editor_ui.directional_shadow_distance_input.text = f"{self.render_settings.directional_shadow_distance:.1f}"
        self.editor_ui.shadow_bias_input.text = f"{self.render_settings.shadow_bias:.4f}"
        self.editor_ui.spot_shadows_enabled = self.render_settings.spot_shadows_enabled
        self.editor_ui.spot_shadow_resolution_input.text = str(self.render_settings.spot_shadow_resolution)
        self.editor_ui.ambient_strength_input.text = f"{self.render_settings.ambient_strength:.2f}"
        self.editor_ui.ambient_color_input.text = "#FFFFFF"
        self.editor_ui.sun_azimuth_input.text = f"{self.render_settings.sun_azimuth_deg:.1f}"
        self.editor_ui.sun_elevation_input.text = f"{self.render_settings.sun_elevation_deg:.1f}"
        self.editor_ui.sun_intensity_input.text = f"{self.render_settings.sun_intensity:.2f}"
        self._saved_transforms = {}
        self._pending_spawns = []
        self._pending_destroys = []
        self._undo_stack = []
        self._redo_stack = []
        self._history_last_signature = None
        self._history_suspend = False
        self._history_replaying = False
        self._skip_snapshot_frames = 0  # Skip N frames after undo/redo to avoid clearing redo

        self._build_scene()
        self.editor_ui.set_scene_context(self.current_scene_file, self.list_scene_files())
        self.editor_ui.set_prefab_context(self.list_prefab_names())
        self._record_history_snapshot(force=True)
        
        # Synchronize play-mode state on startup so camera snaps correctly without F1
        self.dev_mode = True
        self.toggle_dev_mode() # This sets dev_mode to False and primes scripts/input/cursor

        self.clock = pygame.time.Clock()
        self.time = 0.0

    def on_resize(self, new_size):
        """Handle OS window resize and notify dependent subsystems."""
        w, h = int(new_size[0]), int(new_size[1])
        if w <= 0 or h <= 0:
            return

        self.win_size = (w, h)
        pygame.display.set_mode(
            self.win_size,
            flags=pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE,
        )

        self.hud.win_size = self.win_size
        self.editor_ui.win_size = self.win_size
        self.scene_hierarchy.win_size = self.win_size
        # Recompute panel positions on next draw (match PANEL_WIDTH in editor_ui)
        self.editor_ui.panel_x = self.win_size[0] - 340 - 10

        if hasattr(self.renderer, "resize"):
            self.renderer.resize(w, h)

    # ------------------------------------------------------------------
    # Scene
    # ------------------------------------------------------------------

    def _build_scene(self):
        self.static_objects = []

        self.light_orb = LightOrb(self.ctx)
        self.static_objects.append(self.light_orb)

        self.scene_objects, self.model_meshes, settings = load_scene(
            self.current_scene_file, self.ctx, self.texture_loader, 
            resource_manager=self.resource_manager
        )
        self.editor_ui.set_prefab_context(self.list_prefab_names())
        
        # Apply marker-based spawn on boot
        self._apply_spawn_logic()

        # Register physics before scripts run
        for obj in self.scene_objects:
            self.physics_system.add_object(obj)
        self._rebuild_renderables()
        # Place the light orb roughly along the main light direction so the
        # user can see where the sun is.
        sun_pos = glm.vec3(self.editor_camera.position) - self.main_light_dir * 20.0
        self.light_orb.transform.position = sun_pos

    @property
    def active_camera(self):
        """Returns the Editor Camera in dev mode, or the Play Camera if one is set.
        Cutscene playback overrides the editor camera even in dev mode."""
        if self.play_camera:
            return self.play_camera
        if self.dev_mode:
            return self.editor_camera
        return self.editor_camera

    def set_play_camera(self, camera):
        """Allows a script (e.g. Player) to register a new perspective in Play Mode."""
        self.play_camera = camera

    @property
    def input_enabled(self):
        """Returns False if cutscene is playing with can_player_move=False."""
        if self.cutscenes.is_playing and not self.cutscenes.can_player_move:
            return False
        return True

    def _rebuild_renderables(self):
        self.all_renderables = list(self.static_objects)
        for obj in self.scene_objects:
            self.all_renderables.extend(obj.meshes)

    # ------------------------------------------------------------------
    # UI Utils
    # ------------------------------------------------------------------

    def show_image_overlay(self, path, duration):
        """Display a full-screen image for the given duration."""
        self.hud.show_image(path, duration)

    # ------------------------------------------------------------------
    # Tag queries
    # ------------------------------------------------------------------

    def find_by_tag(self, tag):
        """Return a list of all SceneObjects with the given tag."""
        return [o for o in self.scene_objects if getattr(o, 'tag', '') == tag]

    def _apply_spawn_logic(self, override_pos=None, override_rot=None):
        """Finds the player and snaps them to the correct starting point.
        Hierarchy: 1. Manual Overrides (Transitions) > 2. Scene 'player_spawn' Marker > 3. Default JSON pos.
        """
        player = self.find_one_by_tag('player')
        if not player:
            return

        final_pos = None
        final_rot = None

        # 1. Manual Overrides (usually from Door script or command line)
        if override_pos is not None:
            final_pos = glm.vec3(override_pos)
            print(f"[Spawn] Logic: Transition Override -> {final_pos}")
        if override_rot is not None:
            final_rot = override_rot

        # 2. Scene Marker (an object tagged or named 'player_spawn')
        if final_pos is None:
            marker = None
            for obj in self.scene_objects:
                tag = getattr(obj, 'tag', '').lower()
                name = getattr(obj, 'name', '').lower()
                if tag == 'player_spawn' or name == 'player_spawn':
                    marker = obj
                    break
            
            if marker:
                final_pos = glm.vec3(marker.position)
                # Extract Euler from the marker's rotation
                e = marker.rotation_euler
                final_rot = [e.x, e.y, e.z]
                print(f"[Spawn] Logic: Marker ('{marker.name}') -> {final_pos}")
                # Hide spawn markers in play mode (vague heuristic)
                if not self.dev_mode:
                    marker.is_collideable = False
            else:
                print(f"[Spawn] Logic: Default JSON (No marker found)")

        # Apply results
        if final_pos is not None:
            player.position = final_pos
        if final_rot is not None:
            player.set_rotation_euler(final_rot[0], final_rot[1], final_rot[2])
        
        # Ensure physics is synced immediately
        player._physics_dirty = True

    def find_one_by_tag(self, tag):
        """Return the first SceneObject with the given tag, or None."""
        for o in self.scene_objects:
            if getattr(o, 'tag', '') == tag:
                return o
        return None

    # ------------------------------------------------------------------
    # Runtime spawn / destroy
    # ------------------------------------------------------------------

    def spawn(self, fmt, name='spawned', position=None, scale=None, color=None,
              tag='', scripts=None, **physics_kwargs):
        """Spawn a new object during play mode. Returns the SceneObject."""
        entry = {
            'name': name,
            'format': fmt,
            'position': list(position or [0, 0, 0]),
            'scale': list(scale or [1, 1, 1]),
            'tag': tag,
            'scripts': scripts or [],
        }
        if color is not None:
            entry['color'] = list(color)
        for k, v in physics_kwargs.items():
            entry[k] = v

        obj = spawn_from_entry(entry, self.ctx, self.texture_loader, 
                              shader_cache=self.shader_cache, resource_manager=self.resource_manager)
        if obj is None:
            return None
        self._pending_spawns.append(obj)
        return obj

    def _ensure_unique_name(self, base_name):
        """Return base_name or base_name_N so it does not collide with existing objects."""
        existing = {o.name for o in self.scene_objects}
        existing.update(o.name for o in self._pending_spawns)
        if base_name not in existing:
            return base_name
        n = 1
        while f"{base_name}_{n}" in existing:
            n += 1
        return f"{base_name}_{n}"

    def spawn_prefab(self, prefab_name, position=None, tag=None, name=None):
        """Instantiate a saved prefab. Position/tag/name override the template."""
        data = load_prefab(prefab_name)
        if data is None:
            return None
        if position is not None:
            data['position'] = list(position)
        if tag is not None:
            data['tag'] = tag
        if name is not None:
            data['name'] = name
        else:
            data['name'] = self._ensure_unique_name(data.get('name', 'prefab'))

        obj = spawn_from_entry(data, self.ctx, self.texture_loader, 
                              shader_cache=self.shader_cache, resource_manager=self.resource_manager)
        if obj is None:
            return None
        self._pending_spawns.append(obj)
        return obj

    def save_prefab(self, obj, prefab_name):
        """Save an existing SceneObject as a reusable prefab."""
        return save_prefab(obj, prefab_name)

    def destroy(self, obj):
        """Mark a SceneObject for removal (processed at end of frame)."""
        if obj not in self._pending_destroys:
            self._pending_destroys.append(obj)

    def _flush_spawn_destroy(self):
        """Apply pending spawns and destroys. Called once per frame."""
        changed = False

        for obj in self._pending_spawns:
            self.scene_objects.append(obj)
            changed = True
        self._pending_spawns.clear()

        for obj in self._pending_destroys:
            self.physics_system.remove_object(obj)
            for m in obj.meshes:
                m.destroy()
            if obj in self.scene_objects:
                idx = self.scene_objects.index(obj)
                self.scene_objects.remove(obj)
                if self.selected_index >= len(self.scene_objects):
                    self.selected_index = len(self.scene_objects) - 1
            changed = True
        self._pending_destroys.clear()

        if changed:
            self._rebuild_renderables()
            if self.dev_mode:
                self._record_history_snapshot(force=True)

    # ------------------------------------------------------------------
    # Scene switching
    # ------------------------------------------------------------------

    def _build_scene_settings(self):
        """Collect all scene-level settings into a dict for saving."""
        rs = self.render_settings
        return {
            'gravity':                      self.physics_system.gravity,
            'sun_intensity':                rs.sun_intensity,
            'sun_azimuth_deg':              rs.sun_azimuth_deg,
            'sun_elevation_deg':            rs.sun_elevation_deg,
            'ambient_strength':             rs.ambient_strength,
            'ambient_color_r':              rs.ambient_color_r,
            'ambient_color_g':              rs.ambient_color_g,
            'ambient_color_b':              rs.ambient_color_b,
            'directional_shadows_enabled':  rs.directional_shadows_enabled,
            'directional_shadow_distance':  rs.directional_shadow_distance,
            'skybox_path':                  rs.skybox_path,
        }

    def _apply_scene_settings(self, settings):
        """Apply a settings dict (from scene JSON or state snapshot) to the engine."""
        gravity = settings.get('gravity', -9.81)
        self.physics_system.set_gravity(gravity)
        self.editor_ui.update_gravity_ui(gravity)

        rs = self.render_settings
        # Only override values that are explicitly present in the scene JSON so
        # scenes that don't specify a key keep whatever the user has configured.
        if 'sun_intensity' in settings:
            rs.sun_intensity = float(settings['sun_intensity'])
            self.editor_ui.sun_intensity_input.text = f"{rs.sun_intensity:.2f}"
        if 'sun_azimuth_deg' in settings:
            rs.sun_azimuth_deg = float(settings['sun_azimuth_deg'])
            self.editor_ui.sun_azimuth_input.text = f"{rs.sun_azimuth_deg:.1f}"
        if 'sun_elevation_deg' in settings:
            rs.sun_elevation_deg = float(settings['sun_elevation_deg'])
            self.editor_ui.sun_elevation_input.text = f"{rs.sun_elevation_deg:.1f}"
        if 'ambient_strength' in settings:
            rs.ambient_strength = float(settings['ambient_strength'])
            self.editor_ui.ambient_strength_input.text = f"{rs.ambient_strength:.2f}"
        if 'ambient_color_r' in settings:
            rs.ambient_color_r = float(settings['ambient_color_r'])
        if 'ambient_color_g' in settings:
            rs.ambient_color_g = float(settings['ambient_color_g'])
        if 'ambient_color_b' in settings:
            rs.ambient_color_b = float(settings['ambient_color_b'])
        if 'directional_shadows_enabled' in settings:
            rs.directional_shadows_enabled = bool(settings['directional_shadows_enabled'])
            self.editor_ui.directional_shadows_enabled = rs.directional_shadows_enabled
        if 'directional_shadow_distance' in settings:
            rs.directional_shadow_distance = float(settings['directional_shadow_distance'])
            self.editor_ui.directional_shadow_distance_input.text = f"{rs.directional_shadow_distance:.1f}"
        if 'skybox_path' in settings:
            rs.skybox_path = settings['skybox_path'] or ''
            self.renderer.set_skybox(rs.skybox_path, self.texture_loader)
            self.editor_ui.skybox_path_input.text = rs.skybox_path

    def load_scene(self, scene_path, spawn_pos=None, spawn_rot=None):
        """Tear down the current scene and load a new one.
        Can be called from scripts to switch levels. Optional spawn point overrides."""
        self.script_manager.stop_all()
        self.physics_system.reset()

        for obj in self.scene_objects:
            for m in obj.meshes:
                m.destroy()
        self.scene_objects.clear()
        self.model_meshes = []
        self.selected_index = -1
        self._saved_transforms.clear()
        self._pending_spawns.clear()
        self._pending_destroys.clear()

        self.current_scene_file = scene_path
        self.scene_objects, self.model_meshes, settings = load_scene(
            scene_path, self.ctx, self.texture_loader, resource_manager=self.resource_manager
        )
        # Sync UI and settings
        self._apply_scene_settings(settings)
        self.editor_ui.set_scene_context(self.current_scene_file, self.list_scene_files())
        self.editor_ui.set_prefab_context(self.list_prefab_names())

        # Apply spawn logic (marker-based or manual override)
        self._apply_spawn_logic(spawn_pos, spawn_rot)

        # Register physics before scripts run
        for obj in self.scene_objects:
            self.physics_system.add_object(obj)

        self._rebuild_renderables()
        self._undo_stack = []
        self._redo_stack = []
        self._history_last_signature = None
        self._record_history_snapshot(force=True)

        if not self.dev_mode:
            self._saved_transforms = {}
            for obj in self.scene_objects:
                euler = obj.rotation_euler
                self._saved_transforms[id(obj)] = {
                    'position': glm.vec3(obj.position),
                    'rotation_euler': (euler.x, euler.y, euler.z),
                    'scale': glm.vec3(obj.scale),
                }
            self.script_manager.load_scripts(self, self.scene_objects)

        print(f"[Engine] Scene loaded: {scene_path}")

    # ------------------------------------------------------------------
    # Save As
    # ------------------------------------------------------------------

    def _save_as(self, filename):
        safe_name = "".join(c for c in filename if c.isalnum() or c in ('_', '-'))
        if not safe_name:
            safe_name = "untitled"
        path = os.path.join('scenes', f'{safe_name}.json')
        os.makedirs('scenes', exist_ok=True)
        save_scene(path, self.scene_objects, settings=self._build_scene_settings())
        self.current_scene_file = path
        self.editor_ui.set_scene_context(self.current_scene_file, self.list_scene_files())
        self._record_history_snapshot(force=True)
        print(f"[DevMode] Scene saved as: {path}")

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self):
        dt = self.clock.tick(60) / 1000.0
        self.time += dt

        if not self.cursor_mode and self.dev_mode:
            self.active_camera.process_keyboard(dt)

        if self.dev_mode and self.selected_index >= 0 and not self.cursor_mode:
            self.dev_tools.handle_movement_keys(dt, self.scene_objects, self.selected_index)

        if self.cursor_mode and self.dev_mode:
            self.dev_tools.apply_ui_properties(
                self.scene_objects, self.selected_index, self.editor_ui
            )

        # Ensure Play Intro config matches UI
        if hasattr(self.editor_ui, 'play_intro_enabled'):
            self.play_intro_enabled = self.editor_ui.play_intro_enabled

        # Autosave
        if self.autosave_enabled and self.dev_mode:
            self.autosave_timer += dt
            if self.autosave_timer >= AUTOSAVE_INTERVAL:
                self.autosave_timer = 0.0
                save_scene(self.current_scene_file, self.scene_objects, settings=self._build_scene_settings())
                print("[Autosave] Scene saved")

        # Physics and scripts only run in play mode.
        if not self.dev_mode:
            self.interaction_manager.update()
            num_steps = self.physics_system.step(dt, self.scene_objects)
            for _ in range(num_steps):
                self.script_manager.fixed_update_all(FIXED_TIMESTEP)
            if self.physics_system.collisions:
                self.script_manager.dispatch_collisions(self.physics_system.collisions)
            self.script_manager.update_all(dt)
            self.dialogue.update(dt)

        self.hud.update(dt)

        # Cutscene updates in all modes when playing
        if self.cutscenes.is_playing:
            self.cutscenes.update(dt)
            try:
                speed = float(self.editor_ui.cutscene_speed_input.text)
                self.cutscenes.playback_speed = max(0.1, speed)
            except ValueError:
                pass
            self.cutscenes.can_player_move = self.editor_ui.cutscene_can_player_move
            self.cutscenes.is_looping = self.editor_ui.cutscene_is_looping

        # Update editor UI
        sel_obj = None
        if 0 <= self.selected_index < len(self.scene_objects):
            sel_obj = self.scene_objects[self.selected_index]
            
        # Check and apply global gravity from UI
        if self.dev_mode:
            try:
                new_grav = float(self.editor_ui.global_gravity_input.text)
                self.physics_system.set_gravity(new_grav)
            except ValueError:
                pass

            # Apply retro render settings from UI (all toggleable)
            rs = self.render_settings
            rs.ps2_enabled = bool(getattr(self.editor_ui, "ps2_enabled", True))
            rs.postprocess_enabled = bool(getattr(self.editor_ui, "postprocess_enabled", True))
            rs.quantize_enabled = bool(getattr(self.editor_ui, "quantize_enabled", True))
            rs.dither_enabled = bool(getattr(self.editor_ui, "dither_enabled", False))
            rs.lighting_ramp_enabled = bool(getattr(self.editor_ui, "lighting_ramp_enabled", True))
            rs.specular_banding_enabled = bool(getattr(self.editor_ui, "specular_banding_enabled", False))
            rs.wobble_enabled = bool(getattr(self.editor_ui, "wobble_enabled", False))

            def _parse_int(text, default, lo, hi):
                try:
                    v = int(str(text).strip())
                    return max(lo, min(hi, v))
                except Exception:
                    return default

            rs.pixel_size = _parse_int(getattr(self.editor_ui, "pixel_size_input", None).text if getattr(self.editor_ui, "pixel_size_input", None) else rs.pixel_size, rs.pixel_size, 1, 32)
            rs.quantize_steps = _parse_int(getattr(self.editor_ui, "quantize_steps_input", None).text if getattr(self.editor_ui, "quantize_steps_input", None) else rs.quantize_steps, rs.quantize_steps, 2, 256)
            rs.lighting_ramp_steps = _parse_int(getattr(self.editor_ui, "lighting_ramp_steps_input", None).text if getattr(self.editor_ui, "lighting_ramp_steps_input", None) else rs.lighting_ramp_steps, rs.lighting_ramp_steps, 1, 16)
            rs.specular_steps = _parse_int(getattr(self.editor_ui, "specular_steps_input", None).text if getattr(self.editor_ui, "specular_steps_input", None) else rs.specular_steps, rs.specular_steps, 1, 16)
            rs.wobble_pixel_size = _parse_int(getattr(self.editor_ui, "wobble_pixel_input", None).text if getattr(self.editor_ui, "wobble_pixel_input", None) else rs.wobble_pixel_size, rs.wobble_pixel_size, 1, 16)
            rs.directional_shadows_enabled = bool(getattr(self.editor_ui, "directional_shadows_enabled", True))
            rs.spot_shadows_enabled = bool(getattr(self.editor_ui, "spot_shadows_enabled", True))
            rs.directional_shadow_resolution = _parse_int(getattr(self.editor_ui, "directional_shadow_resolution_input", None).text if getattr(self.editor_ui, "directional_shadow_resolution_input", None) else rs.directional_shadow_resolution, rs.directional_shadow_resolution, 256, 4096)
            rs.spot_shadow_resolution = _parse_int(getattr(self.editor_ui, "spot_shadow_resolution_input", None).text if getattr(self.editor_ui, "spot_shadow_resolution_input", None) else rs.spot_shadow_resolution, rs.spot_shadow_resolution, 256, 2048)

            try:
                rs.directional_shadow_distance = max(4.0, min(200.0, float(self.editor_ui.directional_shadow_distance_input.text)))
            except Exception:
                pass
            try:
                rs.shadow_bias = max(0.0001, min(0.03, float(self.editor_ui.shadow_bias_input.text)))
            except Exception:
                pass
            try:
                rs.ambient_strength = max(0.0, min(1.0, float(self.editor_ui.ambient_strength_input.text)))
            except Exception:
                pass
            try:
                rs.sun_azimuth_deg = float(self.editor_ui.sun_azimuth_input.text)
                rs.sun_elevation_deg = float(self.editor_ui.sun_elevation_input.text)
            except Exception:
                pass
            try:
                rs.sun_intensity = max(0.0, min(5.0, float(self.editor_ui.sun_intensity_input.text)))
            except Exception:
                pass
            amb = EditorUI._parse_hex(getattr(self.editor_ui, "ambient_color_input", None).text if getattr(self.editor_ui, "ambient_color_input", None) else "#FFFFFF")
            if amb:
                rs.ambient_color_r = amb[0] / 255.0
                rs.ambient_color_g = amb[1] / 255.0
                rs.ambient_color_b = amb[2] / 255.0
            new_sky = self.editor_ui.skybox_path_input.text.strip()
            if new_sky != rs.skybox_path:
                rs.skybox_path = new_sky
                self.renderer.set_skybox(new_sky, self.texture_loader)

        # Update sun direction and orb position every frame so it doesn't jump
        rs = self.render_settings
        az = math.radians(rs.sun_azimuth_deg)
        el = math.radians(rs.sun_elevation_deg)
        self.main_light_dir = glm.normalize(glm.vec3(
            math.cos(el) * math.cos(az),
            math.sin(el),
            math.cos(el) * math.sin(az),
        ))
        if hasattr(self, "light_orb"):
            # Place the sun orb on a large radius sphere so it appears fixed in the sky
            radius = 50.0
            sun_pos = -self.main_light_dir * radius
            self.light_orb.transform.position = sun_pos
                
        # Only refresh context when scene list could have changed (not every frame)
        # The UI context is already set during scene loading and save operations.
        self.editor_ui.update(dt, pygame.mouse.get_pos(), sel_obj)
        if sel_obj:
            self.editor_ui.refresh_values(sel_obj)

        # Update hierarchy panel
        self.scene_hierarchy.update(pygame.mouse.get_pos(), self.scene_objects)

        for obj in self.all_renderables:
            obj.update(dt)

        for obj in self.scene_objects:
            if not self.dev_mode:
                if getattr(obj, 'anim_state_controller', None) is not None and getattr(obj, 'use_anim_state_controller', False):
                    obj.anim_state_controller.update(dt, obj=obj, physics_system=self.physics_system)
                if obj.animator is not None:
                    obj.animator.update(dt)
                    # If non-skinned, apply root bone to object transform
                    if obj.meshes and not getattr(obj.meshes[0], '_has_skin', False):
                        p, r, s = obj.animator.get_root_transform()
                        if p is not None:
                            obj.position = p
                            # obj.rotation is a quat in SceneObject
                            for m in obj.meshes:
                                m.transform.rotation = r
                            obj.scale = s
                            obj._physics_dirty = True

        # HUD info
        if sel_obj:
            self.hud.selected_name = f"{sel_obj.name} (id={sel_obj.id})"
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

        self._flush_spawn_destroy()
        if self.dev_mode:
            self._record_history_snapshot()

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
        # Scale the main light color by sun_intensity (0 = indoor, no sun)
        sun_int = float(getattr(self.render_settings, 'sun_intensity', 1.0))
        effective_sun_color = self.light_color * sun_int
        self.renderer.render(
            self.all_renderables, self.scene_objects, self.active_camera, self.hud,
            self.light_pos, self.light_color,
            self.dev_mode, self.selected_index,
            render_settings=self.render_settings,
            win_size=self.win_size,
            main_light_dir=self.main_light_dir,
            main_light_color=effective_sun_color,
            dialogue_active=self.dialogue.active,
        )

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def play_intro(self):
        intro_path = os.path.join('assets', 'videos', 'intro.mp4')
        if os.path.exists(intro_path) and self.play_intro_enabled:
            from core.video_player import VideoPlayer
            player = VideoPlayer(self.ctx, self.shader_cache, intro_path)
            if player.valid:
                player.play(skip_sec=0.5, fade_in_sec=1.0)
            player.destroy()

    def run(self):
        if PLAY_INTRO:
            self.play_intro()
        
        # Reset clock so time spent in video doesn't cause a huge dt update jump
        self.clock.tick()
        
        while True:
            self.input_handler.process_events()
            self.update()
            self.render()

    def _quit(self):
        self.audio.destroy()
        for obj in self.all_renderables:
            obj.destroy()
        self.texture_loader.destroy()
        self.hud.destroy()
        pygame.quit()
        sys.exit()