"""PrefabManager — save and instantiate reusable object templates."""

import json
import os
import glm
from core.serialization import serialize_scene_object

PREFAB_DIR = 'prefabs'


def _ensure_dir():
    os.makedirs(PREFAB_DIR, exist_ok=True)


def save_prefab(obj, prefab_name):
    """Serialize a SceneObject's configuration to a JSON prefab file."""
    _ensure_dir()
    data = serialize_scene_object(obj)

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
