"""Unified scene object serialization for the BigChicken Engine.

This module provides a single source of truth for serializing SceneObjects
to dicts, used by engine.py, scene_loader.py, and prefab_manager.py.
"""


def _serialize_vec3(v, precision=3):
    """Safely serialize a glm.vec3 or a list to a [x, y, z] list."""
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return [round(float(x), precision) for x in v]
    # Assume glm.vec3/vec4
    return [round(float(v.x), precision), round(float(v.y), precision), round(float(v.z), precision)]


def serialize_scene_object(obj):
    """Serialize a SceneObject to a dict for JSON storage.

    This function consolidates serialization logic from multiple locations
    to ensure consistent behavior across Undo/Redo, Scene Save, and Prefab Save.
    """
    entry = {
        "name": obj.name,
        "format": obj.format,
        "position": _serialize_vec3(obj.position),
        "rotation": _serialize_vec3(obj.rotation_euler),
        "scale": _serialize_vec3(obj.scale, 4),
        "mass": round(float(obj.mass), 3),
        "use_gravity": bool(obj.use_gravity),
        "is_collideable": bool(getattr(obj, "is_collideable", True)),
        "is_kinematic": bool(obj.is_kinematic),
        "collider_type": str(obj.collider_type),
        "bounciness": round(float(obj.bounciness), 3),
        "friction": round(float(obj.friction), 3),
        "drag_linear": round(float(obj.drag), 3),
        "tag": str(getattr(obj, 'tag', '')),
        "scripts": obj.scripts.copy() if hasattr(obj, 'scripts') else [],
        "casts_shadows": bool(getattr(obj, 'casts_shadows', True)),
        "receives_shadows": bool(getattr(obj, 'receives_shadows', True)),
        "is_trigger": bool(getattr(obj, 'is_trigger', False)),
        "dialogue_data": getattr(obj, 'dialogue_data', None),
    }

    if obj.format not in ('cube', 'triangle', 'light', 'sprite'):
        entry["model"] = str(obj.model_path)

    if obj.format == 'sprite' and obj.meshes:
        sprite_mesh = obj.meshes[0]
        entry["sprite_path"] = str(getattr(sprite_mesh, 'image_path', ''))
        entry["billboard"] = bool(getattr(sprite_mesh, 'billboard', True))
        entry["autocrop"] = bool(getattr(sprite_mesh, 'autocrop', True))

    if obj.format in ('cube', 'triangle') and obj.meshes:
        entry["color"] = _serialize_vec3(obj.meshes[0].color)

    if getattr(obj, 'is_light', False):
        entry["intensity"] = float(obj.light_intensity)
        lc = obj.light_color
        if lc is None and obj.meshes:
            lc = getattr(obj.meshes[0], 'color', None)
        entry["color"] = _serialize_vec3(lc) if lc else [1.0, 1.0, 1.0]
        entry["light_casts_shadows"] = bool(getattr(obj, 'light_casts_shadows', True))

    if obj.alpha < 1.0:
        entry["alpha"] = round(float(obj.alpha), 3)

    if getattr(obj, 'folder', 'Scene') != 'Scene':
        entry["folder"] = str(obj.folder)

    if getattr(obj, 'interactable', False):
        entry["interactable"] = True
        entry["use_view_interaction"] = bool(getattr(obj, 'use_view_interaction', False))
        entry["interaction_distance"] = round(float(getattr(obj, 'interaction_distance', 3.0)), 3)

    # Dialogue camera overrides — only write when set so the JSON stays clean.
    dcp = getattr(obj, 'dialogue_cam_pos', None)
    if dcp is not None:
        entry["dialogue_cam_pos"] = _serialize_vec3(dcp)
    dcy = getattr(obj, 'dialogue_cam_yaw', None)
    if dcy is not None:
        entry["dialogue_cam_yaw"] = round(float(dcy), 2)
    dcp2 = getattr(obj, 'dialogue_cam_pitch', None)
    if dcp2 is not None:
        entry["dialogue_cam_pitch"] = round(float(dcp2), 2)
    if getattr(obj, 'animator', None) is not None:
        entry["use_anim_state_controller"] = bool(getattr(obj, 'use_anim_state_controller', False))
        cfg = getattr(obj, 'anim_state_config', {})
        entry["anim_state"] = {
            "idle": str(cfg.get('idle', 'idle')),
            "run": str(cfg.get('run', 'run')),
            "jump": str(cfg.get('jump', 'jump')),
            "fall": str(cfg.get('fall', 'fall')),
            "move_threshold": float(cfg.get('move_threshold', 0.1)),
            "vertical_threshold": float(cfg.get('vertical_threshold', 0.15)),
        }

    # Persist custom script variables (e.g., used by SceneTrigger)
    scene_path = getattr(obj, 'scene_path', None)
    if scene_path is not None:
        entry["scene_path"] = str(scene_path)

    tp = getattr(obj, 'target_position', None)
    if tp is not None:
        entry["target_position"] = _serialize_vec3(tp)

    tr = getattr(obj, 'target_rotation', None)
    if tr is not None:
        entry["target_rotation"] = _serialize_vec3(tr)

    return entry
