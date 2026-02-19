"""Dev mode — spawning, deletion, object manipulation, and scene info."""

import pygame
from pyglm import glm
from scene import Cube, Triangle, LightOrb
from core.scene_loader import SceneObject


class DevMode:
    """Manages dev-mode state: spawning, selecting, moving/scaling objects."""

    def __init__(self):
        self.cube_counter = 0
        self.tri_counter = 0
        self.light_counter = 0
        self.move_speed = 2.0
        self.scale_speed = 1.5

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    def spawn_at(self, ctx, obj_type, position, scene_objects, rebuild_fn, editor_ui):
        """Spawn an object at a specific world position. Returns new selected index."""
        if obj_type == 'cube':
            self.cube_counter += 1
            name = f"cube_{self.cube_counter}"
            mesh = Cube(ctx, color=glm.vec3(0.49, 0.48, 1.0))
            fmt = 'cube'
        elif obj_type == 'triangle':
            self.tri_counter += 1
            name = f"tri_{self.tri_counter}"
            mesh = Triangle(ctx, color=glm.vec3(1.0, 0.4, 0.2))
            fmt = 'triangle'
        elif obj_type == 'light':
            self.light_counter += 1
            name = f"light_{self.light_counter}"
            mesh = LightOrb(ctx, radius=0.3, color=glm.vec3(1.0, 1.0, 0.9))
            fmt = 'light'
        else:
            return -1

        spawn_pos = glm.vec3(position.x, position.y + 0.5, position.z)
        mesh.transform.position = glm.vec3(spawn_pos)
        mesh.transform.scale = glm.vec3(1.0)

        is_light = (obj_type == 'light')
        obj = SceneObject(name, '', fmt, [mesh], is_light=is_light)
        scene_objects.append(obj)
        rebuild_fn()

        editor_ui._current_obj_name = None
        print(f"[DevMode] Placed {obj_type} '{name}' at ({spawn_pos.x:.1f}, {spawn_pos.y:.1f}, {spawn_pos.z:.1f})")
        return len(scene_objects) - 1

    def spawn_in_front(self, ctx, obj_type, camera, scene_objects, rebuild_fn, editor_ui):
        """Spawn 5 units in front of camera."""
        pos = camera.position + camera.front * 5.0
        return self.spawn_at(ctx, obj_type, pos, scene_objects, rebuild_fn, editor_ui)

    def delete_selected(self, scene_objects, selected_index, rebuild_fn, editor_ui):
        """Delete the selected object. Returns new selected index (-1)."""
        if selected_index < 0:
            return selected_index
        obj = scene_objects[selected_index]
        print(f"[DevMode] Deleted '{obj.name}'")
        for m in obj.meshes:
            m.destroy()
        scene_objects.pop(selected_index)
        editor_ui._current_obj_name = None
        rebuild_fn()
        return -1

    # ------------------------------------------------------------------
    # Object manipulation
    # ------------------------------------------------------------------

    def handle_movement_keys(self, dt, scene_objects, selected_index):
        """Handle arrow/Q/E movement and +/- scaling for selected object."""
        if selected_index < 0 or selected_index >= len(scene_objects):
            return
        keys = pygame.key.get_pressed()
        obj = scene_objects[selected_index]
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
    # UI property application
    # ------------------------------------------------------------------

    def apply_ui_properties(self, scene_objects, selected_index, editor_ui):
        """Read values from editor UI and apply to the selected object."""
        if selected_index < 0 or selected_index >= len(scene_objects):
            return
        obj = scene_objects[selected_index]
        if editor_ui._current_obj_name != obj.name:
            return
        values = editor_ui.read_property_values()

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

        from core.editor_ui import EditorUI
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

        # Intensity (lights only)
        intensity_val = values.get('intensity', '')
        if intensity_val and obj.is_light:
            try:
                obj.light_intensity = max(0.0, float(intensity_val))
            except (ValueError, TypeError):
                pass

        # Alpha (all objects)
        alpha_val = values.get('alpha', '')
        if alpha_val:
            try:
                obj.alpha = float(alpha_val)
            except (ValueError, TypeError):
                pass

        # Folder assignment — only apply when field is not being actively edited
        folder_info = editor_ui.prop_inputs.get('folder')
        if folder_info and folder_info.get('field'):
            field = folder_info['field']
            if not field.active:
                folder_val = field.text.strip()
                if folder_val and folder_val != getattr(obj, 'folder', 'Scene'):
                    obj.folder = folder_val

    # ------------------------------------------------------------------
    # Scene info
    # ------------------------------------------------------------------

    @staticmethod
    def print_scene_info(scene_file, scene_objects, selected_index):
        """Print scene info to console."""
        print("\n" + "=" * 60)
        print(f"  SCENE: {scene_file}")
        print(f"  Objects: {len(scene_objects)}")
        print("=" * 60)
        for i, obj in enumerate(scene_objects):
            p = obj.position
            s = obj.scale
            sel = " [SELECTED]" if i == selected_index else ""
            kind = " (light)" if obj.is_light else ""
            print(f"  [{i}] {obj.name} ({obj.format}){kind}{sel}")
            if obj.model_path:
                print(f"      Model:    {obj.model_path}")
            print(f"      Position: ({p.x:.2f}, {p.y:.2f}, {p.z:.2f})")
            print(f"      Scale:    ({s.x:.4f}, {s.y:.4f}, {s.z:.4f})")
        print("=" * 60 + "\n")
