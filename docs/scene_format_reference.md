# Scene Format Reference

Scenes are JSON files in `scenes/`.

Top-level structure:

```json
{
  "settings": {
    "gravity": -9.81
  },
  "objects": []
}
```

## Object Schema

Common fields:
- `name` (string)
- `format` (string): `cube`, `triangle`, `light`, `obj`, `glb`, `gltf`
- `position` ([x, y, z])
- `rotation` ([pitch, yaw, roll], degrees)
- `scale` ([x, y, z])
- `mass` (float)
- `use_gravity` (bool)
- `is_kinematic` (bool)
- `collider_type` (string: usually `box`; `sphere` and `mesh` are supported by physics)
- `bounciness` (float)
- `friction` (float)
- `drag_linear` (float)
- `tag` (string)
- `scripts` (array of script names)
- `alpha` (float 0..1, optional)
- `folder` (string, optional)

Format-specific fields:
- `obj`/`glb`/`gltf`: requires `model` path
- `cube`/`triangle`: optional `color` ([r, g, b], 0..1)
- `light`: optional `color`, `intensity`

## Example: Primitive + Light

```json
{
  "settings": { "gravity": -9.81 },
  "objects": [
    {
      "name": "floor",
      "format": "cube",
      "position": [0, -0.05, 0],
      "rotation": [0, 0, 0],
      "scale": [50, 0.1, 50],
      "color": [0.35, 0.35, 0.4],
      "mass": 0.0,
      "use_gravity": false,
      "is_kinematic": true,
      "collider_type": "box",
      "bounciness": 0.0,
      "friction": 0.5,
      "drag_linear": 0.02,
      "tag": "ground",
      "scripts": []
    },
    {
      "name": "lamp",
      "format": "light",
      "position": [3, 4, 2],
      "rotation": [0, 0, 0],
      "scale": [1, 1, 1],
      "intensity": 2.0,
      "color": [1.0, 0.95, 0.8],
      "mass": 0.0,
      "use_gravity": false,
      "is_kinematic": true,
      "collider_type": "box",
      "bounciness": 0.0,
      "friction": 0.5,
      "drag_linear": 0.02,
      "tag": "light",
      "scripts": []
    }
  ]
}
```

## Example: Model with Scripts and Tag

```json
{
  "name": "player",
  "format": "glb",
  "model": "assets/models/player.glb",
  "position": [0, 1, 0],
  "rotation": [0, 0, 0],
  "scale": [1, 1, 1],
  "mass": 1.0,
  "use_gravity": true,
  "is_kinematic": false,
  "collider_type": "box",
  "bounciness": 0.1,
  "friction": 0.6,
  "drag_linear": 0.02,
  "tag": "player",
  "scripts": ["player_controller", "camera_follow"]
}
```

## Notes and Compatibility

- Script names are normalized by loader and script manager:
  - `scripts/player_controller.py` -> `player_controller`
- Legacy scenes using `drag` instead of `friction` are tolerated:
  - if `drag` exists and `friction` is missing, loader maps it for compatibility
- Missing model file logs a warning and skips that object

## Best Practices

- Keep scene JSON under source control
- Use small, focused script names (`enemy_ai`, `door_trigger`)
- Prefer tags for gameplay queries (`enemy`, `pickup`, `spawned`)
- Keep folder names stable so hierarchy/export organization stays consistent
