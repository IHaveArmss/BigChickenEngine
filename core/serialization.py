"""Unified scene object serialization for the BigChicken Engine.

This module provides a single source of truth for serializing SceneObjects
to dicts, used by engine.py, scene_loader.py, and prefab_manager.py.
"""


def serialize_scene_object(obj):
    """Serialize a SceneObject to a dict for JSON storage.

    This function consolidates serialization logic from multiple locations
    to ensure consistent behavior across Undo/Redo, Scene Save, and Prefab Save.
    """
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
        "is_collideable": getattr(obj, "is_collideable", True),
        "is_kinematic": obj.is_kinematic,
        "collider_type": obj.collider_type,
        "bounciness": round(obj.bounciness, 3),
        "friction": round(obj.friction, 3),
        "drag_linear": round(obj.drag, 3),
        "tag": getattr(obj, 'tag', ''),
        "scripts": obj.scripts.copy() if hasattr(obj, 'scripts') else [],
        "casts_shadows": bool(getattr(obj, 'casts_shadows', True)),
        "receives_shadows": bool(getattr(obj, 'receives_shadows', True)),
        "is_trigger": bool(getattr(obj, 'is_trigger', False)),
        "dialogue_data": getattr(obj, 'dialogue_data', None),
    }

    if obj.format not in ('cube', 'triangle', 'light', 'sprite'):
        entry["model"] = obj.model_path

    if obj.format == 'sprite' and obj.meshes:
        sprite_mesh = obj.meshes[0]
        entry["sprite_path"] = getattr(sprite_mesh, 'image_path', '')
        entry["billboard"] = getattr(sprite_mesh, 'billboard', True)
        entry["autocrop"] = getattr(sprite_mesh, 'autocrop', True)

    if obj.format in ('cube', 'triangle') and obj.meshes:
        c = obj.meshes[0].color
        entry["color"] = [round(c.x, 3), round(c.y, 3), round(c.z, 3)]

    if getattr(obj, 'is_light', False):
        entry["intensity"] = obj.light_intensity
        lc = obj.light_color
        if lc is None and obj.meshes:
            lc = getattr(obj.meshes[0], 'color', None)
        if lc:
            entry["color"] = [round(lc.x, 3), round(lc.y, 3), round(lc.z, 3)]
        else:
            entry["color"] = [1.0, 1.0, 1.0]
        entry["light_casts_shadows"] = bool(getattr(obj, 'light_casts_shadows', True))

    if obj.alpha < 1.0:
        entry["alpha"] = round(obj.alpha, 3)

    if getattr(obj, 'folder', 'Scene') != 'Scene':
        entry["folder"] = obj.folder

    if getattr(obj, 'interactable', False):
        entry["interactable"] = True
        entry["interaction_distance"] = round(getattr(obj, 'interaction_distance', 3.0), 3)

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

    return entry
