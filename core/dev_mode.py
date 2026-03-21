"""Dev mode — spawning, deletion, object manipulation, and scene info."""

import pygame
import glm
from scene import Cube, Triangle, LightOrb
from core.scene_loader import SceneObject
from core.animation_state_controller import AnimationStateController


def _normalize_script_names(raw_scripts):
    """Normalize script names from UI/list input into unique names without extension."""
    if raw_scripts is None:
        return []

    if isinstance(raw_scripts, str):
        parts = raw_scripts.replace('\n', ',').replace(';', ',').split(',')
    else:
        parts = []
        for item in raw_scripts:
            if isinstance(item, str):
                parts.extend(item.replace('\n', ',').replace(';', ',').split(','))

    normalized = []
    seen = set()
    for s in parts:
        name = s.strip().strip('"').strip("'").replace('\\', '/')
        if not name:
            continue
        if name.startswith('scripts/'):
            name = name[8:]
        if name.endswith('.py'):
            name = name[:-3]
        if name and name not in seen:
            seen.add(name)
            normalized.append(name)
    return normalized


def _sync_anim_state_controller(obj):
    animator = getattr(obj, 'animator', None)
    if animator is None:
        obj.anim_state_controller = None
        obj.use_anim_state_controller = False
        return

    if not getattr(obj, 'use_anim_state_controller', False):
        obj.anim_state_controller = None
        return

    cfg = getattr(obj, 'anim_state_config', {})
    obj.anim_state_controller = AnimationStateController(
        animator,
        idle_clip=cfg.get('idle', 'idle'),
        run_clip=cfg.get('run', 'run'),
        jump_clip=cfg.get('jump', 'jump'),
        fall_clip=cfg.get('fall', 'fall'),
        move_threshold=float(cfg.get('move_threshold', 0.1)),
        vertical_threshold=float(cfg.get('vertical_threshold', 0.15)),
    )


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
        lc = mesh.color if is_light else None
        obj = SceneObject(name, '', fmt, [mesh], is_light=is_light, light_color=lc)
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
            rx = float(values.get('rot_x', obj.rotation_euler.x))
            ry = float(values.get('rot_y', obj.rotation_euler.y))
            rz = float(values.get('rot_z', obj.rotation_euler.z))
            obj.set_rotation_euler(rx, ry, rz)
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
                
        # --- Physics Properties ---
        try:
            if 'mass' in values: obj.mass = max(0.0, float(values['mass']))
            if 'bounciness' in values: obj.bounciness = max(0.0, float(values['bounciness']))
            if 'friction' in values: obj.friction = max(0.0, float(values['friction']))
            if 'drag' in values: obj.drag = max(0.0, float(values['drag']))
        except (ValueError, TypeError):
            pass
            
        if 'use_gravity' in values:
            obj.use_gravity = (values['use_gravity'] == True)
        if 'is_kinematic' in values:
            obj.is_kinematic = (values['is_kinematic'] == True)
        if 'casts_shadows' in values:
            obj.casts_shadows = (values['casts_shadows'] is True)
        if 'receives_shadows' in values:
            obj.receives_shadows = (values['receives_shadows'] is True)
        if 'light_casts_shadows' in values and obj.is_light:
            obj.light_casts_shadows = (values['light_casts_shadows'] is True)
        if 'collider_type' in values:
            obj.collider_type = str(values['collider_type'])
            
        obj._physics_dirty = True

        # Animation state controller options (for skinned/animated objects)
        if getattr(obj, 'animator', None) is not None:
            cfg = getattr(obj, 'anim_state_config', {})
            old_state = (
                bool(getattr(obj, 'use_anim_state_controller', False)),
                str(cfg.get('idle', 'idle')),
                str(cfg.get('run', 'run')),
                str(cfg.get('jump', 'jump')),
                str(cfg.get('fall', 'fall')),
                float(cfg.get('move_threshold', 0.1)),
                float(cfg.get('vertical_threshold', 0.15)),
            )
            if 'use_anim_state_controller' in values:
                obj.use_anim_state_controller = (values['use_anim_state_controller'] is True)
            if 'anim_idle' in values:
                cfg['idle'] = str(values['anim_idle']).strip() or cfg.get('idle', 'idle')
            if 'anim_run' in values:
                cfg['run'] = str(values['anim_run']).strip() or cfg.get('run', 'run')
            if 'anim_jump' in values:
                cfg['jump'] = str(values['anim_jump']).strip() or cfg.get('jump', 'jump')
            if 'anim_fall' in values:
                cfg['fall'] = str(values['anim_fall']).strip() or cfg.get('fall', 'fall')
            try:
                if 'anim_move_threshold' in values:
                    cfg['move_threshold'] = max(0.0, float(values['anim_move_threshold']))
                if 'anim_vertical_threshold' in values:
                    cfg['vertical_threshold'] = max(0.0, float(values['anim_vertical_threshold']))
            except (ValueError, TypeError):
                pass
            obj.anim_state_config = cfg
            new_state = (
                bool(getattr(obj, 'use_anim_state_controller', False)),
                str(cfg.get('idle', 'idle')),
                str(cfg.get('run', 'run')),
                str(cfg.get('jump', 'jump')),
                str(cfg.get('fall', 'fall')),
                float(cfg.get('move_threshold', 0.1)),
                float(cfg.get('vertical_threshold', 0.15)),
            )
            if new_state != old_state:
                _sync_anim_state_controller(obj)

        # Folder assignment — only apply when field is not being actively edited
        folder_info = editor_ui.prop_inputs.get('folder')
        if folder_info and folder_info.get('field'):
            field = folder_info['field']
            if not field.active:
                folder_val = field.text.strip()
                if folder_val and folder_val != getattr(obj, 'folder', 'Scene'):
                    obj.folder = folder_val

        # Scripts are managed via explicit Add/Remove actions from the editor UI.
        
    def handle_anim_action(self, action, scene_objects, selected_index, editor_ui):
        """Handle animation-related actions from the UI."""
        if selected_index < 0 or selected_index >= len(scene_objects):
            return
        obj = scene_objects[selected_index]
        act_type = action.get('action')
        
        if act_type == 'anim_record_toggle':
            # Record current transform as a keyframe
            pos = glm.vec3(obj.position)
            rot = glm.vec3(obj.rotation_euler)
            scl = glm.vec3(obj.scale)
            
            # Use specified interval for time
            interval = 0.5
            try:
                interval = float(editor_ui.anim_interval.text)
            except ValueError:
                pass
            
            t = len(editor_ui.recorded_keyframes) * interval
            editor_ui.recorded_keyframes.append({
                'time': t,
                'pos': pos,
                'rot': rot,
                'scl': scl
            })
            print(f"[DevMode] Recorded keyframe {len(editor_ui.recorded_keyframes)} for '{obj.name}'")
            
        elif act_type == 'anim_play':
            clip_name = action.get('name', 'new_clip')
            if obj.animator:
                obj.animator.play(clip_name)
                print(f"[DevMode] Playing clip '{clip_name}' on '{obj.name}'")
            
        elif act_type == 'anim_stop':
            if obj.animator:
                obj.animator.stop()
                print(f"[DevMode] Stopped animation on '{obj.name}'")
                
        elif act_type == 'anim_clear':
            editor_ui.recorded_keyframes = []
            print(f"[DevMode] Cleared keyframes for '{obj.name}'")
            
        elif act_type == 'anim_save':
            name = action.get('name', 'new_clip').strip()
            smooth = action.get('smooth', True)
            if not name:
                print("[DevMode] Save failed: no clip name")
                return
            if not editor_ui.recorded_keyframes:
                print("[DevMode] Save failed: no keyframes recorded")
                return
            
            self._create_transform_clip(obj, name, editor_ui.recorded_keyframes, smooth=smooth)
            editor_ui.recorded_keyframes = []
            print(f"[DevMode] Saved animation clip '{name}' to '{obj.name}'")

    def _create_transform_clip(self, obj, name, keyframes, smooth=True):
        """Convert recorded keyframes into an AnimationClip and attach to object."""
        from core.animator import Animator, AnimationClip, Channel, Skeleton
        
        interp = 'LINEAR' if smooth else 'STEP'
        
        if not obj.animator:
            # Create a dummy skeleton for transform-only animation
            dummy_skeleton = Skeleton(
                joint_names=['root'],
                parent_indices=[-1],
                inverse_bind_matrices=[glm.mat4(1.0)],
                bind_translations=[glm.vec3(0)],
                bind_rotations=[glm.quat(1, 0, 0, 0)],
                bind_scales=[glm.vec3(1)]
            )
            obj.animator = Animator(dummy_skeleton, {})
            
        # Create Channels
        # In our engine, bone_index -1 can mean "object transform itself" 
        # but the current animator expects bone indices. 
        # Let's use bone 0 (root) and make sure the mesh is parented or the animator 
        # applies to the root bone.
        
        times = [kf['time'] for kf in keyframes]
        positions = [kf['pos'] for kf in keyframes]
        
        # Convert euler to quat for rotation channel
        rotations = []
        for kf in keyframes:
            r = kf['rot']
            # glm.quat is (w, x, y, z) or (x, y, z, w) depending on version, 
            # BCE seems to use glm.quat(euler_vec3)
            q = glm.quat(glm.vec3(glm.radians(r.x), glm.radians(r.y), glm.radians(r.z)))
            rotations.append(q)
            
        scales = [kf['scl'] for kf in keyframes]
        
        # We'll create 3 channels for the root bone (index 0)
        c_pos = Channel(0, 'translation', times, positions, interpolation=interp)
        c_rot = Channel(0, 'rotation', times, rotations, interpolation=interp)
        c_scl = Channel(0, 'scale', times, scales, interpolation=interp)
        
        duration = max(times) if times else 0
        new_clip = AnimationClip(name, duration, [c_pos, c_rot, c_scl])
        
        # Add to animator
        obj.animator.clips[name] = new_clip
        if obj.animator.clip_names:
            obj.animator.clip_names.append(name)
        else:
            obj.animator.clip_names = [name]

    def add_scripts(self, scene_objects, selected_index, raw_scripts, editor_ui):
        """Add one or more scripts to selected object (deduplicated)."""
        if selected_index < 0 or selected_index >= len(scene_objects):
            return
        obj = scene_objects[selected_index]
        incoming = _normalize_script_names(raw_scripts)
        if not incoming:
            return

        current = _normalize_script_names(getattr(obj, 'scripts', []))
        merged = list(current)
        for s in incoming:
            if s not in merged:
                merged.append(s)
        obj.scripts = merged

        scripts_info = editor_ui.prop_inputs.get('scripts')
        if scripts_info and scripts_info.get('field'):
            scripts_info['field'].text = ''

        print(f"[DevMode] Added scripts to '{obj.name}': {', '.join(incoming)}")

    def remove_scripts(self, scene_objects, selected_index, raw_scripts, editor_ui):
        """Remove one or more scripts from selected object."""
        if selected_index < 0 or selected_index >= len(scene_objects):
            return
        obj = scene_objects[selected_index]
        targets = set(_normalize_script_names(raw_scripts))
        if not targets:
            return

        current = _normalize_script_names(getattr(obj, 'scripts', []))
        updated = [s for s in current if s not in targets]
        obj.scripts = updated

        scripts_info = editor_ui.prop_inputs.get('scripts')
        if scripts_info and scripts_info.get('field'):
            scripts_info['field'].text = ''

        print(f"[DevMode] Removed scripts from '{obj.name}': {', '.join(sorted(targets))}")

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
