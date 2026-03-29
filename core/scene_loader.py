"""Scene loader — reads a scene JSON file and spawns model/primitive objects."""

import json
import os
import math
import glm
from core.model_loader import load_obj, load_gltf
from core.model_mesh import ModelMesh
from core.animator import Animator
from core.animation_state_controller import AnimationStateController
from core.utils import normalize_script_names
from core.serialization import serialize_scene_object
from scene import Cube, Triangle, LightOrb


class SceneObject:
    """Wrapper that groups all meshes belonging to one named object."""

    _next_id = 1

    def __init__(self, name, model_path, fmt, meshes, is_light=False,
                 light_intensity=1.0, light_color=None, alpha=1.0,
                 folder='Scene', tag=''):
        self.id = SceneObject._next_id
        SceneObject._next_id += 1
        self.name = name
        self.model_path = model_path
        self.format = fmt
        self.meshes = meshes
        self.is_light = is_light
        self.light_intensity = light_intensity
        self.light_color = light_color
        self.folder = folder
        self.tag = tag
        self.interactable = False
        self.use_view_interaction = False
        self.interaction_distance = 3.0
        self.is_hovered = False
        self._alpha = alpha
        self.scripts = []
        self.casts_shadows = True
        self.receives_shadows = True

        self.is_trigger = False
        self.dialogue_data = None
        
        # Physics Properties
        self.pybullet_body_id = None
        self.is_collideable = True
        self.mass = 1.0
        self.use_gravity = False
        self.is_kinematic = True
        self.collider_type = 'box'
        self.collider_scale = None  # If set, used for physics instead of visual scale
        self.bounciness = 0.0
        self.friction = 0.5
        self.drag = 0.02
        self._physics_dirty = True
        self.animator = None
        self.anim_state_controller = None
        self.use_anim_state_controller = False
        self.light_casts_shadows = True
        self.anim_state_config = {
            'idle': 'idle',
            'run': 'run',
            'jump': 'jump',
            'fall': 'fall',
            'move_threshold': 0.1,
            'vertical_threshold': 0.15,
        }

        # Backing store for position/scale/rotation when meshes is empty
        self._position = glm.vec3(0)
        self._scale = glm.vec3(1)
        self._rotation = glm.quat()
        self._rotation_euler = glm.vec3(0)

        for m in self.meshes:
            m.alpha = self._alpha
            m.owner_obj = self

    @property
    def position(self):
        if self.meshes:
            return self.meshes[0].transform.position
        return self._position

    @position.setter
    def position(self, value):
        if self.meshes:
            for m in self.meshes:
                m.transform.position = glm.vec3(value)
        else:
            self._position = glm.vec3(value)
        self._physics_dirty = True

    @property
    def scale(self):
        if self.meshes:
            return self.meshes[0].transform.scale
        return self._scale

    @scale.setter
    def scale(self, value):
        if self.meshes:
            for m in self.meshes:
                m.transform.scale = glm.vec3(value)
        else:
            self._scale = glm.vec3(value)

    @property
    def rotation(self):
        if self.meshes:
            return self.meshes[0].transform.rotation
        return self._rotation

    @property
    def rotation_euler(self):
        return self._rotation_euler

    def set_rotation_euler(self, pitch, yaw, roll):
        self._rotation_euler = glm.vec3(pitch, yaw, roll)
        if self.meshes:
            for m in self.meshes:
                m.transform.rotation = glm.quat(glm.vec3(
                    glm.radians(pitch), glm.radians(yaw), glm.radians(roll)
                ))
        else:
            self._rotation = glm.quat(glm.vec3(
                glm.radians(pitch), glm.radians(yaw), glm.radians(roll)
            ))

    def update_transform(self, pos, quat):
        """Internal sync from physics engine — does NOT mark physics as dirty."""
        for m in self.meshes:
            m.transform.position = glm.vec3(pos)
            # PyBullet (x,y,z,w) -> GLM (w,x,y,z)
            m.transform.rotation = glm.quat(quat[3], quat[0], quat[1], quat[2])

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = max(0.0, min(1.0, value))
        for m in self.meshes:
            m.alpha = self._alpha


def spawn_from_entry(entry, ctx, texture_loader, shader_cache=None, resource_manager=None):
    """Create a single SceneObject from a dict (used by load_scene, spawn, and prefabs).
    Returns the SceneObject or None if the model is missing."""
    from core.sprite_mesh import SpriteMesh
    
    name = entry.get('name', 'unnamed')
    model_path = entry.get('model', '')
    fmt = entry.get('format', 'obj')
    pos = entry.get('position', [0, 0, 0])
    rot = entry.get('rotation', [0, 0, 0])
    scl = entry.get('scale', [1, 1, 1])
    color = entry.get('color', None)

    if fmt == 'cube':
        c = color or [0.49, 0.48, 1.0]
        cube = Cube(ctx, color=glm.vec3(*c[:3]), shader_cache=shader_cache)
        cube.transform.position = glm.vec3(*pos)
        cube.transform.scale = glm.vec3(*scl)
        meshes = [cube]
        obj = SceneObject(name, '', 'cube', meshes,
                          alpha=entry.get('alpha', 1.0),
                          folder=entry.get('folder', 'Scene'),
                          tag=entry.get('tag', ''))

    elif fmt == 'triangle':
        c = color or [1.0, 0.4, 0.2]
        tri = Triangle(ctx, color=glm.vec3(*c[:3]), shader_cache=shader_cache)
        tri.transform.position = glm.vec3(*pos)
        tri.transform.scale = glm.vec3(*scl)
        meshes = [tri]
        obj = SceneObject(name, '', 'triangle', meshes,
                          alpha=entry.get('alpha', 1.0),
                          folder=entry.get('folder', 'Scene'),
                          tag=entry.get('tag', ''))

    elif fmt == 'light':
        intensity = entry.get('intensity', 1.0)
        lc = color or [1.0, 1.0, 0.9]
        orb = LightOrb(ctx, radius=0.3, color=glm.vec3(*lc[:3]), shader_cache=shader_cache)
        orb.transform.position = glm.vec3(*pos)
        orb.transform.scale = glm.vec3(*scl)
        meshes = [orb]
        obj = SceneObject(name, '', 'light', meshes,
                          is_light=True, light_intensity=intensity,
                          light_color=glm.vec3(*lc[:3]),
                          alpha=entry.get('alpha', 1.0),
                          folder=entry.get('folder', 'Scene'),
                          tag=entry.get('tag', ''))
    
    elif fmt == 'sprite':
        sprite_path = entry.get('sprite_path', '')
        if not sprite_path or not os.path.exists(sprite_path):
            print(f"[SceneLoader] WARNING: sprite not found: {sprite_path}")
            return None
        
        billboard = entry.get('billboard', True)
        autocrop = entry.get('autocrop', True)
        
        try:
            sprite = SpriteMesh(ctx, texture_loader, sprite_path, shader_cache=shader_cache,
                             autocrop=autocrop, billboard=billboard)
        except Exception as e:
            print(f"[SceneLoader] WARNING: failed to create sprite: {e}")
            return None
        
        sprite.transform.position = glm.vec3(*pos)
        sprite.transform.scale = glm.vec3(*scl)
        meshes = [sprite]
        obj = SceneObject(name, '', 'sprite', meshes,
                          alpha=entry.get('alpha', 1.0),
                          folder=entry.get('folder', 'Scene'),
                          tag=entry.get('tag', ''))
        obj.collider_type = 'box'
        obj.is_kinematic = True
        obj.use_gravity = False
        obj.mass = 0.0
    
    else:
        if not os.path.exists(model_path):
            print(f"[SceneLoader] WARNING: model not found: {model_path}")
            return None

        if resource_manager:
            mesh_datas = resource_manager.get_model_data(model_path, fmt)
        else:
            if fmt in ('glb', 'gltf'):
                mesh_datas = load_gltf(model_path)
            else:
                mesh_datas = load_obj(model_path)

        meshes = []
        skeleton_data = None
        animations_data = None
        for md in mesh_datas:
            m = ModelMesh(ctx, md, texture_loader)
            m.transform.position = glm.vec3(*pos)
            m.transform.scale = glm.vec3(*scl)
            meshes.append(m)
            if md.get('has_skin') and skeleton_data is None:
                skeleton_data = md.get('skeleton')
                animations_data = md.get('animations')

        obj = SceneObject(name, model_path, fmt, meshes,
                          alpha=entry.get('alpha', 1.0),
                          folder=entry.get('folder', 'Scene'),
                          tag=entry.get('tag', ''))

        # Initialize Animator if the model has a skeleton
        if skeleton_data:
            # We initialize even if animations_data is empty, allowing
            # for external injection of clips (e.g. via cata_anims.glb)
            animator = Animator(skeleton_data, animations_data or {})
            obj.animator = animator
            for m in meshes:
                if getattr(m, '_has_skin', False):
                    m.animator = animator
            if animations_data:
                first_clip = next(iter(animations_data))
                animator.play(first_clip)
            print(f"[SceneLoader]   -> Skeleton with {skeleton_data.num_joints} bones, "
                  f"{len(animations_data)} animation(s)")

            # External animation injection (if requested or hardcoded)
            # MUST happen BEFORE state controller is created so clips exist when _resolve_clips() runs
            anim_src = entry.get('animation_source')

            # PERMANENT FALLBACK: If no animation source is provided, use Cata's defaults
            if not anim_src and 'catahobov1.glb' in model_path.lower():
                anim_src = [
                    'assets/animations/player/Idle.glb', 
                    'assets/animations/player/Running.glb',
                    'assets/animations/player/Jump.glb',
                    'assets/animations/player/Falling.glb',
                    'assets/animations/playerGun/pistol_Idle.glb',
                    'assets/animations/playerGun/pistol_run.glb',
                    'assets/animations/playerGun/pistol_jump.glb'
                ]
            
            # SUIT FALLBACK: If no animation source is provided, use Formal Suit defaults
            if not anim_src and any(m in model_path.lower() for m in ['osuit.glb', 'cata_formal_tpose.glb', 'cata_formal_idle.glb']):
                anim_src = [
                    'assets/animations/playerSuit/cata_formal_idle.glb', 
                    'assets/animations/playerSuit/cata_formal_run.glb',
                    'assets/animations/playerSuit/cata_formal_jump.glb',
                    'assets/animations/playerSuit/cata_formal_falling.glb',
                    'assets/animations/playerSuitGun/cata_formal_idle_pistol.glb',
                    'assets/animations/playerSuitGun/cata_formal_run_pistol.glb',
                    'assets/animations/playerSuitGun/cata_formal_jump_pistol.glb'
                ]

            if anim_src:
                # Support single string or list of strings
                if isinstance(anim_src, str):
                    sources = [anim_src]
                else:
                    sources = anim_src

                for src in sources:
                    if os.path.exists(src):
                        # Extract basename as a potential clip name (e.g. Idle.glb -> Idle)
                        base_name = os.path.splitext(os.path.basename(src))[0]
                        
                        external_mesh_datas = load_gltf(src)
                        if external_mesh_datas:
                            for emd in external_mesh_datas:
                                if emd.get('has_skin'):
                                    # Use cached data if available via the resource manager
                                    anim_data = emd.get('animations')
                                    if resource_manager:
                                        ext_data = resource_manager.get_model_data(src, 'glb')
                                        if ext_data:
                                            for ed in ext_data:
                                                if ed.get('has_skin'):
                                                    anim_data = ed.get('animations')
                                                    break
                                    
                                    # SMART RENAME: If there's only 1 animation, rename it to the file's name
                                    # This prevents conflicts between files, regardless of what the modeling software exported it as.
                                    if len(anim_data) == 1:
                                        original_name = list(anim_data.keys())[0]
                                        print(f"[SceneLoader] Found 1 animation '{original_name}' in {base_name}.glb, renaming to '{base_name}'")
                                        clip = anim_data.pop(original_name)
                                        clip.name = base_name
                                        anim_data[base_name] = clip
                                    
                                    animator.rebind_clips(anim_data, emd.get('skeleton'))
                                    break
                    else:
                        print(f"[SceneLoader] WARNING: animation_source file not found: {src}")

            # Optional auto state-machine controller for character-like animation.
            cfg = entry.get('anim_state', {})
            obj.anim_state_config.update({
                'idle': cfg.get('idle', obj.anim_state_config['idle']),
                'run': cfg.get('run', obj.anim_state_config['run']),
                'jump': cfg.get('jump', obj.anim_state_config['jump']),
                'fall': cfg.get('fall', obj.anim_state_config['fall']),
                'move_threshold': cfg.get('move_threshold', obj.anim_state_config['move_threshold']),
                'vertical_threshold': cfg.get('vertical_threshold', obj.anim_state_config['vertical_threshold']),
            })
            obj.use_anim_state_controller = bool(entry.get('use_anim_state_controller', False))
            if obj.use_anim_state_controller:
                obj.anim_state_controller = AnimationStateController(
                    animator,
                    idle_clip=obj.anim_state_config['idle'],
                    run_clip=obj.anim_state_config['run'],
                    jump_clip=obj.anim_state_config['jump'],
                    fall_clip=obj.anim_state_config['fall'],
                    move_threshold=float(obj.anim_state_config['move_threshold']),
                    vertical_threshold=float(obj.anim_state_config['vertical_threshold']),
                )

            # PERMANENT FALLBACK: Force Animation State Controller for the player (Hobo or Suit)
            if not obj.anim_state_controller:
                if 'catahobov1.glb' in model_path.lower():
                    obj.anim_state_controller = AnimationStateController(
                        animator,
                        idle_clip='Idle',
                        run_clip='Running',
                        jump_clip='Jump',
                        fall_clip='Falling',
                        move_threshold=0.1,
                        vertical_threshold=0.15
                    )
                    obj.use_anim_state_controller = True
                elif any(m in model_path.lower() for m in ['osuit.glb', 'cata_formal_tpose.glb', 'cata_formal_idle.glb']):
                    obj.anim_state_controller = AnimationStateController(
                        animator,
                        idle_clip='cata_formal_idle',
                        run_clip='cata_formal_run',
                        jump_clip='cata_formal_jump',
                        fall_clip='cata_formal_falling',
                        move_threshold=0.1,
                        vertical_threshold=0.15
                    )
                    obj.use_anim_state_controller = True

    obj.mass = entry.get('mass', 1.0)
    obj.use_gravity = entry.get('use_gravity', False)
    obj.is_collideable = entry.get('is_collideable', True)
    obj.is_kinematic = entry.get('is_kinematic', True)
    default_collider = 'mesh' if fmt in ('glb', 'gltf') else 'box'
    obj.collider_type = entry.get('collider_type', default_collider)
    obj.bounciness = entry.get('bounciness', 0.0)

    # Optional physics-only scale override (decouples visual scale from collider size)
    raw_cs = entry.get('collider_scale', None)
    obj.collider_scale = raw_cs  # stored as list or None; physics system handles it

    # Friction: prefer 'friction', fall back to 'drag' for legacy scenes
    if 'friction' in entry:
        obj.friction = entry['friction']
    elif 'drag' in entry:
        obj.friction = entry['drag']
    else:
        obj.friction = 0.5

    # Drag: prefer 'drag_linear', fall back to 'drag' for legacy scenes
    if 'drag_linear' in entry:
        obj.drag = entry['drag_linear']
    elif 'drag' in entry:
        obj.drag = entry['drag']
    else:
        obj.drag = 0.02

    obj.scripts = normalize_script_names(entry.get('scripts', []))
    obj.interactable = bool(entry.get('interactable', False))
    obj.use_view_interaction = bool(entry.get('use_view_interaction', False))
    obj.interaction_distance = float(entry.get('interaction_distance', 3.0))
    obj.casts_shadows = bool(entry.get('casts_shadows', True))
    obj.receives_shadows = bool(entry.get('receives_shadows', True))
    obj.light_casts_shadows = bool(entry.get('light_casts_shadows', obj.is_light))
    obj.is_trigger = bool(entry.get('is_trigger', False))
    obj.dialogue_data = entry.get('dialogue_data', None)

    # Optional dialogue camera overrides.
    # dialogue_cam_pos:   [x, y, z]  — exact world-space camera position during dialogue
    # dialogue_cam_yaw:   float      — camera horizontal angle in degrees
    # dialogue_cam_pitch: float      — camera vertical angle in degrees
    raw_dcp = entry.get('dialogue_cam_pos')
    obj.dialogue_cam_pos   = glm.vec3(*raw_dcp) if raw_dcp else None
    obj.dialogue_cam_yaw   = entry.get('dialogue_cam_yaw', None)
    obj.dialogue_cam_pitch = entry.get('dialogue_cam_pitch', None)

    if any(r != 0 for r in rot):
        obj.set_rotation_euler(*rot)

    for m in obj.meshes:
        m.owner_obj = obj

    # Apply visual offset and rotation to meshes
    visual_offset = entry.get('visual_offset', None)
    visual_rotation = entry.get('visual_rotation', None)

    # PERMANENT FALLBACK: If no offset/rotation is provided in JSON, check for model-specific defaults
    if visual_offset is None:
        if any(m in model_path.lower() for m in ['osuit.glb', 'cata_formal_idle.glb', 'cata_formal_tpose.glb', 'ayan_']):
            visual_offset = [0, 0, 0]
        elif 'catahobov1.glb' in model_path.lower():
            visual_offset = [0, -0.39, 0]
        else:
            visual_offset = [0, 0, 0]

    if visual_rotation is None:
        if any(m in model_path.lower() for m in ['osuit.glb', 'cata_formal_idle.glb', 'cata_formal_tpose.glb', 'ayan_']):
            # Suit/Ayan characters usually need to be stood up 90 degrees
            visual_rotation = [90, 0, 0]
        else:
            visual_rotation = [0, 0, 0]

    for m in obj.meshes:
        if hasattr(m, 'visual_offset'):
            m.visual_offset = glm.vec3(*visual_offset)
        if hasattr(m, 'visual_rotation'):
            m.visual_rotation = glm.vec3(*visual_rotation)

    obj.interactable = entry.get('interactable', False)
    obj.use_view_interaction = entry.get('use_view_interaction', False)
    obj.interaction_distance = entry.get('interaction_distance', 5.0)
    obj.interactable_text = entry.get('interactable_text', 'Press E to interact')

    # Pass all other generic properties to the object so scripts can access them
    standard_keys = {
        'name', 'format', 'position', 'rotation', 'scale', 'mass', 'use_gravity',
        'is_collideable', 'is_kinematic', 'collider_type', 'collider_scale', 'bounciness', 'friction',
        'drag_linear', 'tag', 'scripts', 'casts_shadows', 'receives_shadows', 'is_trigger',
        'dialogue_data', 'color', 'model', 'animation_source', 'use_anim_state_controller',
        'anim_state', 'interactable', 'use_view_interaction', 'interaction_distance', 'alpha'
    }
    for key, value in entry.items():
        if key not in standard_keys:
            setattr(obj, key, value)

    return obj


def load_scene(scene_path, ctx, texture_loader, resource_manager=None):
    """Load a scene JSON file. Returns (scene_objects, all_meshes, settings)."""
    with open(scene_path, 'r') as f:
        data = json.load(f)

    settings = data.get('settings', {'gravity': -9.81})
    scene_objects = []
    all_meshes = []

    for entry in data.get('objects', []):
        obj = spawn_from_entry(entry, ctx, texture_loader, resource_manager=resource_manager)
        if obj is None:
            continue
        all_meshes.extend(obj.meshes)
        scene_objects.append(obj)

    return scene_objects, all_meshes, settings


def save_scene(scene_path, scene_objects, settings=None):
    """Write current scene object transforms back to the JSON file."""
    if settings is None:
        settings = {'gravity': -9.81}
    data = {"settings": settings, "objects": []}

    for obj in scene_objects:
        entry = serialize_scene_object(obj)
        data["objects"].append(entry)

    with open(scene_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"[SceneLoader] Scene saved to {scene_path}")
