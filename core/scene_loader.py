"""Scene loader — reads a scene JSON file and spawns model/primitive objects."""

import json
import os
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
        self.interaction_distance = 3.0
        self.is_hovered = False
        self._alpha = alpha
        self.scripts = []
        self.casts_shadows = True
        self.receives_shadows = True

        # Physics Properties
        self.pybullet_body_id = None
        self.mass = 1.0
        self.use_gravity = False
        self.is_kinematic = True
        self.collider_type = 'box'
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
        if not self.meshes:
            return glm.vec3(0)
        rads = glm.eulerAngles(self.meshes[0].transform.rotation)
        return glm.vec3(glm.degrees(rads.x), glm.degrees(rads.y), glm.degrees(rads.z))

    def set_rotation_euler(self, pitch, yaw, roll):
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


def spawn_from_entry(entry, ctx, texture_loader, shader_cache=None):
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
        cube = Cube(ctx, color=glm.vec3(*c), shader_cache=shader_cache)
        cube.transform.position = glm.vec3(*pos)
        cube.transform.scale = glm.vec3(*scl)
        meshes = [cube]
        obj = SceneObject(name, '', 'cube', meshes,
                          alpha=entry.get('alpha', 1.0),
                          folder=entry.get('folder', 'Scene'),
                          tag=entry.get('tag', ''))

    elif fmt == 'triangle':
        c = color or [1.0, 0.4, 0.2]
        tri = Triangle(ctx, color=glm.vec3(*c), shader_cache=shader_cache)
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
        orb = LightOrb(ctx, radius=0.3, color=glm.vec3(*lc), shader_cache=shader_cache)
        orb.transform.position = glm.vec3(*pos)
        orb.transform.scale = glm.vec3(*scl)
        meshes = [orb]
        obj = SceneObject(name, '', 'light', meshes,
                          is_light=True, light_intensity=intensity,
                          light_color=glm.vec3(*lc),
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
    
    else:
        if not os.path.exists(model_path):
            print(f"[SceneLoader] WARNING: model not found: {model_path}")
            return None

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

        if skeleton_data and animations_data:
            animator = Animator(skeleton_data, animations_data)
            obj.animator = animator
            for m in meshes:
                if getattr(m, '_has_skin', False):
                    m.animator = animator
            if animations_data:
                first_clip = next(iter(animations_data))
                animator.play(first_clip)
            print(f"[SceneLoader]   -> Skeleton with {skeleton_data.num_joints} bones, "
                  f"{len(animations_data)} animation(s)")

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

    obj.mass = entry.get('mass', 1.0)
    obj.use_gravity = entry.get('use_gravity', False)
    obj.is_kinematic = entry.get('is_kinematic', True)
    obj.collider_type = entry.get('collider_type', 'box')
    obj.bounciness = entry.get('bounciness', 0.0)

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
    obj.interaction_distance = float(entry.get('interaction_distance', 3.0))
    obj.casts_shadows = bool(entry.get('casts_shadows', True))
    obj.receives_shadows = bool(entry.get('receives_shadows', True))
    obj.light_casts_shadows = bool(entry.get('light_casts_shadows', obj.is_light))

    if any(r != 0 for r in rot):
        obj.set_rotation_euler(*rot)

    for m in obj.meshes:
        m.owner_obj = obj

    return obj


def load_scene(scene_path, ctx, texture_loader):
    """Load a scene JSON file. Returns (scene_objects, all_meshes, settings)."""
    with open(scene_path, 'r') as f:
        data = json.load(f)

    settings = data.get('settings', {'gravity': -9.81})
    scene_objects = []
    all_meshes = []

    for entry in data.get('objects', []):
        obj = spawn_from_entry(entry, ctx, texture_loader)
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
