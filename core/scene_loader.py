"""Scene loader — reads a scene JSON file and spawns model/primitive objects."""

import json
import os
import glm
from core.model_loader import load_obj, load_gltf
from core.model_mesh import ModelMesh
from core.animator import Animator
from core.animation_state_controller import AnimationStateController
from scene import Cube, Triangle, LightOrb


def _normalize_script_names(raw_scripts):
    """Normalize script names into a unique list without scripts/ prefix or .py."""
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


class SceneObject:
    """Wrapper that groups all meshes belonging to one named object."""

    def __init__(self, name, model_path, fmt, meshes, is_light=False,
                 light_intensity=1.0, light_color=None, alpha=1.0,
                 folder='Scene', tag=''):
        self.name = name
        self.model_path = model_path
        self.format = fmt
        self.meshes = meshes
        self.is_light = is_light
        self.light_intensity = light_intensity
        self.light_color = light_color
        self.folder = folder
        self.tag = tag
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

        for m in self.meshes:
            m.alpha = self._alpha
            m.owner_obj = self

    @property
    def position(self):
        return self.meshes[0].transform.position if self.meshes else glm.vec3(0)

    @position.setter
    def position(self, value):
        for m in self.meshes:
            m.transform.position = glm.vec3(value)
        self._physics_dirty = True

    @property
    def scale(self):
        return self.meshes[0].transform.scale if self.meshes else glm.vec3(1)

    @scale.setter
    def scale(self, value):
        for m in self.meshes:
            m.transform.scale = glm.vec3(value)

    @property
    def rotation(self):
        return self.meshes[0].transform.rotation if self.meshes else glm.quat()

    @property
    def rotation_euler(self):
        if not self.meshes:
            return glm.vec3(0)
        rads = glm.eulerAngles(self.meshes[0].transform.rotation)
        return glm.vec3(glm.degrees(rads.x), glm.degrees(rads.y), glm.degrees(rads.z))

    def set_rotation_euler(self, pitch, yaw, roll):
        for m in self.meshes:
            m.transform.rotation = glm.quat(glm.vec3(
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


def spawn_from_entry(entry, ctx, texture_loader):
    """Create a single SceneObject from a dict (used by load_scene, spawn, and prefabs).
    Returns the SceneObject or None if the model is missing."""
    name = entry.get('name', 'unnamed')
    model_path = entry.get('model', '')
    fmt = entry.get('format', 'obj')
    pos = entry.get('position', [0, 0, 0])
    rot = entry.get('rotation', [0, 0, 0])
    scl = entry.get('scale', [1, 1, 1])
    color = entry.get('color', None)

    if fmt == 'cube':
        c = color or [0.49, 0.48, 1.0]
        cube = Cube(ctx, color=glm.vec3(*c))
        cube.transform.position = glm.vec3(*pos)
        cube.transform.scale = glm.vec3(*scl)
        meshes = [cube]
        obj = SceneObject(name, '', 'cube', meshes,
                          alpha=entry.get('alpha', 1.0),
                          folder=entry.get('folder', 'Scene'),
                          tag=entry.get('tag', ''))

    elif fmt == 'triangle':
        c = color or [1.0, 0.4, 0.2]
        tri = Triangle(ctx, color=glm.vec3(*c))
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
        orb = LightOrb(ctx, radius=0.3, color=glm.vec3(*lc))
        orb.transform.position = glm.vec3(*pos)
        orb.transform.scale = glm.vec3(*scl)
        meshes = [orb]
        obj = SceneObject(name, '', 'light', meshes,
                          is_light=True, light_intensity=intensity,
                          light_color=glm.vec3(*lc),
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
    obj.friction = entry.get('friction', entry.get('drag', 0.5))
    obj.drag = entry.get('drag_linear', entry.get('drag', 0.02))

    if 'drag' in entry and 'friction' not in entry:
        obj.friction = entry['drag']
        obj.drag = 0.02

    obj.scripts = _normalize_script_names(entry.get('scripts', []))
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
        pos = obj.position
        scl = obj.scale
        rot = obj.rotation_euler
        entry = {
            "name": obj.name,
            "format": obj.format,
            "position": [round(pos.x, 3), round(pos.y, 3), round(pos.z, 3)],
            "rotation": [round(rot.x, 3), round(rot.y, 3), round(rot.z, 3)],
            "scale": [round(scl.x, 4), round(scl.y, 4), round(scl.z, 4)],
            "mass": round(obj.mass, 3),
            "use_gravity": obj.use_gravity,
            "is_kinematic": obj.is_kinematic,
            "collider_type": obj.collider_type,
            "bounciness": round(obj.bounciness, 3),
            "friction": round(obj.friction, 3),
            "drag_linear": round(obj.drag, 3),
            "tag": getattr(obj, 'tag', ''),
            "scripts": obj.scripts.copy() if hasattr(obj, 'scripts') else [],
            "casts_shadows": bool(getattr(obj, 'casts_shadows', True)),
            "receives_shadows": bool(getattr(obj, 'receives_shadows', True)),
        }
        if obj.is_light:
            entry["light_casts_shadows"] = bool(getattr(obj, 'light_casts_shadows', True))
        if getattr(obj, 'animator', None) is not None:
            entry["use_anim_state_controller"] = bool(getattr(obj, 'use_anim_state_controller', False))
            cfg = getattr(obj, 'anim_state_config', {})
            entry["anim_state"] = {
                "idle": cfg.get('idle', 'idle'),
                "run": cfg.get('run', 'run'),
                "jump": cfg.get('jump', 'jump'),
                "fall": cfg.get('fall', 'fall'),
                "move_threshold": float(cfg.get('move_threshold', 0.1)),
                "vertical_threshold": float(cfg.get('vertical_threshold', 0.15)),
            }
        if obj.format not in ('cube', 'triangle', 'light'):
            entry["model"] = obj.model_path
        if obj.format in ('cube', 'triangle') and obj.meshes:
            c = obj.meshes[0].color
            entry["color"] = [round(c.x, 3), round(c.y, 3), round(c.z, 3)]
        if obj.is_light:
            entry["intensity"] = obj.light_intensity
            lc = obj.light_color
            if lc is None and obj.meshes:
                lc = getattr(obj.meshes[0], 'color', glm.vec3(1.0))
            if lc:
                entry["color"] = [round(lc.x, 3), round(lc.y, 3), round(lc.z, 3)]
            else:
                entry["color"] = [1.0, 1.0, 1.0]

        if obj.alpha < 1.0:
            entry["alpha"] = round(obj.alpha, 3)
        if obj.folder != 'Scene':
            entry["folder"] = obj.folder


        data["objects"].append(entry)

    with open(scene_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"[SceneLoader] Scene saved to {scene_path}")
