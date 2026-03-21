"""PrefabManager — save and instantiate reusable object templates."""

import json
import os
import glm

PREFAB_DIR = 'prefabs'


def _ensure_dir():
    os.makedirs(PREFAB_DIR, exist_ok=True)


def save_prefab(obj, prefab_name):
    """Serialize a SceneObject's configuration to a JSON prefab file."""
    _ensure_dir()
    pos = obj.position
    scl = obj.scale
    rot = obj.rotation_euler

    data = {
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
        "scripts": list(obj.scripts) if hasattr(obj, 'scripts') else [],
    }
    if getattr(obj, 'animator', None) is not None:
        data["use_anim_state_controller"] = bool(getattr(obj, 'use_anim_state_controller', False))
        cfg = getattr(obj, 'anim_state_config', {})
        data["anim_state"] = {
            "idle": cfg.get('idle', 'idle'),
            "run": cfg.get('run', 'run'),
            "jump": cfg.get('jump', 'jump'),
            "fall": cfg.get('fall', 'fall'),
            "move_threshold": float(cfg.get('move_threshold', 0.1)),
            "vertical_threshold": float(cfg.get('vertical_threshold', 0.15)),
        }
    if obj.format not in ('cube', 'triangle', 'light'):
        data["model"] = obj.model_path
    if obj.format in ('cube', 'triangle') and obj.meshes:
        c = obj.meshes[0].color
        data["color"] = [round(c.x, 3), round(c.y, 3), round(c.z, 3)]
    if getattr(obj, 'is_light', False):
        data["intensity"] = obj.light_intensity
        lc = obj.light_color
        data["color"] = [round(lc.x, 3), round(lc.y, 3), round(lc.z, 3)]
    if obj.alpha < 1.0:
        data["alpha"] = round(obj.alpha, 3)
    if getattr(obj, 'folder', 'Scene') != 'Scene':
        data["folder"] = obj.folder

    path = os.path.join(PREFAB_DIR, f'{prefab_name}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"[Prefab] Saved prefab '{prefab_name}' -> {path}")
    return path


def load_prefab(prefab_name):
    """Load a prefab JSON and return the raw dict (ready for spawn_from_entry)."""
    path = os.path.join(PREFAB_DIR, f'{prefab_name}.json')
    if not os.path.exists(path):
        print(f"[Prefab] WARNING: Prefab not found: {path}")
        return None
    with open(path, 'r') as f:
        return json.load(f)


def list_prefabs():
    """Return a list of available prefab names."""
    _ensure_dir()
    return [os.path.splitext(f)[0] for f in os.listdir(PREFAB_DIR) if f.endswith('.json')]
