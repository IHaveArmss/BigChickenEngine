"""Scene loader — reads a scene JSON file and spawns model/primitive objects."""

import json
import os
import glm
from core.model_loader import load_obj, load_gltf
from core.model_mesh import ModelMesh
from scene import Cube, Triangle, LightOrb


class SceneObject:
    """Wrapper that groups all meshes belonging to one named object."""

    def __init__(self, name, model_path, fmt, meshes, is_light=False,
                 light_intensity=1.0, light_color=None, alpha=1.0,
                 folder='Scene'):
        self.name = name
        self.model_path = model_path
        self.format = fmt
        self.meshes = meshes
        self.is_light = is_light
        self.light_intensity = light_intensity
        self.light_color = light_color or glm.vec3(1.0, 1.0, 0.9)
        self._alpha = alpha
        self.folder = folder
        # Apply initial alpha to all meshes
        for m in self.meshes:
            m.alpha = self._alpha

    @property
    def position(self):
        return self.meshes[0].transform.position if self.meshes else glm.vec3(0)

    @position.setter
    def position(self, value):
        for m in self.meshes:
            m.transform.position = glm.vec3(value)

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

    def set_rotation_euler(self, pitch, yaw, roll):
        for m in self.meshes:
            m.transform.rotation = glm.quat(glm.vec3(
                glm.radians(pitch), glm.radians(yaw), glm.radians(roll)
            ))

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = max(0.0, min(1.0, value))
        for m in self.meshes:
            m.alpha = self._alpha


def load_scene(scene_path, ctx, texture_loader):
    """Load a scene JSON file. Returns (scene_objects, all_meshes)."""
    with open(scene_path, 'r') as f:
        data = json.load(f)

    scene_objects = []
    all_meshes = []

    for entry in data.get('objects', []):
        name = entry.get('name', 'unnamed')
        model_path = entry.get('model', '')
        fmt = entry.get('format', 'obj')
        pos = entry.get('position', [0, 0, 0])
        rot = entry.get('rotation', [0, 0, 0])
        scl = entry.get('scale', [1, 1, 1])
        color = entry.get('color', None)

        if fmt == 'cube':
            print(f"[SceneLoader] Spawning cube '{name}'")
            c = color or [0.49, 0.48, 1.0]
            cube = Cube(ctx, color=glm.vec3(*c))
            cube.transform.position = glm.vec3(*pos)
            cube.transform.scale = glm.vec3(*scl)
            meshes = [cube]
            all_meshes.append(cube)
            obj = SceneObject(name, '', 'cube', meshes,
                              alpha=entry.get('alpha', 1.0),
                              folder=entry.get('folder', 'Scene'))

        elif fmt == 'triangle':
            print(f"[SceneLoader] Spawning triangle '{name}'")
            c = color or [1.0, 0.4, 0.2]
            tri = Triangle(ctx, color=glm.vec3(*c))
            tri.transform.position = glm.vec3(*pos)
            tri.transform.scale = glm.vec3(*scl)
            meshes = [tri]
            all_meshes.append(tri)
            obj = SceneObject(name, '', 'triangle', meshes,
                              alpha=entry.get('alpha', 1.0),
                              folder=entry.get('folder', 'Scene'))

        elif fmt == 'light':
            print(f"[SceneLoader] Spawning light '{name}'")
            intensity = entry.get('intensity', 1.0)
            lc = color or [1.0, 1.0, 0.9]
            orb = LightOrb(ctx, radius=0.3, color=glm.vec3(*lc))
            orb.transform.position = glm.vec3(*pos)
            orb.transform.scale = glm.vec3(*scl)
            meshes = [orb]
            all_meshes.append(orb)
            obj = SceneObject(name, '', 'light', meshes,
                              is_light=True, light_intensity=intensity,
                              light_color=glm.vec3(*lc),
                              alpha=entry.get('alpha', 1.0),
                              folder=entry.get('folder', 'Scene'))

        else:
            # Model file
            if not os.path.exists(model_path):
                print(f"[SceneLoader] WARNING: model not found: {model_path}")
                continue

            print(f"[SceneLoader] Loading '{name}' from {model_path}...")
            if fmt in ('glb', 'gltf'):
                mesh_datas = load_gltf(model_path)
            else:
                mesh_datas = load_obj(model_path)

            meshes = []
            for md in mesh_datas:
                m = ModelMesh(ctx, md, texture_loader)
                m.transform.position = glm.vec3(*pos)
                m.transform.scale = glm.vec3(*scl)
                meshes.append(m)
                all_meshes.append(m)

            obj = SceneObject(name, model_path, fmt, meshes,
                              alpha=entry.get('alpha', 1.0),
                              folder=entry.get('folder', 'Scene'))
            print(f"[SceneLoader]   -> {len(meshes)} mesh(es) loaded")

        if any(r != 0 for r in rot):
            obj.set_rotation_euler(*rot)
        scene_objects.append(obj)

    return scene_objects, all_meshes


def save_scene(scene_path, scene_objects):
    """Write current scene object transforms back to the JSON file."""
    data = {"objects": []}

    for obj in scene_objects:
        pos = obj.position
        scl = obj.scale
        entry = {
            "name": obj.name,
            "format": obj.format,
            "position": [round(pos.x, 3), round(pos.y, 3), round(pos.z, 3)],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [round(scl.x, 4), round(scl.y, 4), round(scl.z, 4)],
        }
        if obj.format not in ('cube', 'triangle', 'light'):
            entry["model"] = obj.model_path
        if obj.format in ('cube', 'triangle') and obj.meshes:
            c = obj.meshes[0].color
            entry["color"] = [round(c.x, 3), round(c.y, 3), round(c.z, 3)]
        if obj.is_light:
            entry["intensity"] = obj.light_intensity
            lc = obj.light_color
            entry["color"] = [round(lc.x, 3), round(lc.y, 3), round(lc.z, 3)]

        if obj.alpha < 1.0:
            entry["alpha"] = round(obj.alpha, 3)
        if obj.folder != 'Scene':
            entry["folder"] = obj.folder


        data["objects"].append(entry)

    with open(scene_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"[SceneLoader] Scene saved to {scene_path}")
