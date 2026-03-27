# BigChicken Engine: Scripting Guide

This guide explains how scripts are loaded, how lifecycle callbacks work, and how to use runtime APIs safely.

## 1) Script File Rules

Scripts live in `scripts/` and are attached to scene objects.

A script file can define either:
- A class matching the file name in PascalCase
  - `camera_follow.py` -> `CameraFollow`
  - `spawn_destroy_test.py` -> `SpawnDestroyTest`
- Or a fallback class named `Script`

The engine injects:
- `self.engine` -> active `GraphicsEngine` instance
- `self.entity` -> `SceneObject` this script is attached to

You do not need a custom `__init__`. If you add one, keep it lightweight.

## 2) Lifecycle

Scripts run only in Play Mode (`F1` to leave Dev Mode).

Order and behavior:
1. `start(self)` - once when scripts are loaded
2. `fixed_update(self, fixed_dt)` - once per physics substep (`1/240` by default)
3. `on_collision(self, collision)` - when physics reports contacts
4. `update(self, dt)` - once per rendered frame
5. `stop(self)` - when leaving Play Mode or scene reload/switch

All callbacks are wrapped in `try/except` by `ScriptManager`; one script error does not crash the engine.

## 3) Collision Object

`on_collision(self, collision)` receives:
- `collision.other` - other `SceneObject`
- `collision.point` - `glm.vec3` world-space contact point
- `collision.normal` - contact normal (from this entity perspective)
- `collision.impulse` - contact impulse magnitude

## 4) Attaching Scripts in Dev UI

Use the **Selected Object -> Scripts** controls:
1. Select object in Dev Mode (`F1`, then `F2` for cursor)
2. Type one or more script names (comma/semicolon/newline supported)
3. Click `Add` -> `Confirm`
4. Enter Play Mode (`F1`) to execute

To detach scripts:
1. Type names in Scripts input
2. Click `Remove` -> `Confirm`

Notes:
- `scripts/` prefix and `.py` extension are optional
- Names are normalized and de-duplicated

## 5) Minimal Script Example

```python
class Script:
    def start(self):
        print(f"Started on {self.entity.name}")

    def update(self, dt):
        rot = self.entity.rotation_euler
        self.entity.set_rotation_euler(rot.x, rot.y + 45.0 * dt, rot.z)
```

## 6) Physics Movement Pattern

Use `fixed_update` for deterministic movement:

```python
import pybullet as p

class PlayerController:
    def start(self):
        self.body_id = self.entity.pybullet_body_id
        self.phys = self.engine.physics_system

    def fixed_update(self, fixed_dt):
        if self.body_id is None:
            return
        p.applyExternalForce(
            self.body_id,
            -1,
            [0, 20, 0],
            [0, 0, 0],
            p.WORLD_FRAME,
            physicsClientId=self.phys.client_id,
        )
```

## 7) Scene and Runtime API Usage

From scripts, use `self.engine` for higher-level behavior:
- Scene switching: `self.engine.load_scene("scenes/demo.json")`
- Runtime spawn: `self.engine.spawn(...)`
- Runtime destroy: `self.engine.destroy(obj)`
- Tags: `self.engine.find_by_tag("enemy")`
- Prefabs: `self.engine.spawn_prefab("test_ball", position=[0, 2, 0])`
- Audio: `self.engine.audio.play_sfx("assets/audio/sfx.wav")`
- Camera override: `self.engine.set_play_camera(custom_camera)`

See `docs/engine_runtime_api.md` for full signatures.

## 8) Animation from Scripts

All objects (skinned and primitive) can expose `self.entity.animator`. 
- **Skinned Models**: Use bone-based skeletal animation.
- **Other Objects**: Use transform-based animations created in the Editor.

Typical usage:
```python
class CharacterAnim:
    def start(self):
        if self.entity.animator:
            self.entity.animator.play("idle")

    def update(self, dt):
        if not self.entity.animator:
            return
        # Example:
        # self.entity.animator.crossfade("run", duration=0.2)
        pass
```

Animator API:
- `play(name, loop=True, speed=1.0)`
- `crossfade(name, duration=0.3, loop=True, speed=1.0)`
- `stop()`
- `clip_names` property
- `is_playing` property

## 9) Best Practices

- Use `start` to cache references (`physics_system`, body ids, target objects).
- Use `fixed_update` for forces/velocities; use `update` for input/state/UI.
- Keep script state per-instance (`self.*`) rather than global variables.
- Guard optional systems:
  - `if self.entity.pybullet_body_id is None: return`
  - `if self.entity.animator is None: return`
- Implement `stop` for cleanup (stop sounds, release resources, reset flags).

## 10) Debugging Scripts

If a script does not run:
1. Confirm it is attached in Dev UI and listed in **Attached**
2. Enter Play Mode (`F1`)
3. Check console for:
   - `[ScriptManager] WARNING: Script not found`
   - class name mismatch warnings
   - traceback from callback errors

If script edits are not reflected:
- Re-enter Play Mode. Modules are reloaded on each `load_scripts`.
