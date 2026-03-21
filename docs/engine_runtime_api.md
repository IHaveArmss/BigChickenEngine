# Engine Runtime API (for Scripts)

This is the practical API surface scripts use through `self.engine`.

## Core References

Inside every script instance:
- `self.engine`: `GraphicsEngine`
- `self.entity`: current `SceneObject`

## Camera and Mode

### `self.engine.active_camera`
Returns current camera:
- editor camera in Dev Mode
- play camera if set in Play Mode

### `self.engine.set_play_camera(camera)`
Overrides active camera during Play Mode.

## Scene Queries

### `self.engine.find_by_tag(tag) -> list[SceneObject]`
Returns all scene objects with exact matching tag.

### `self.engine.find_one_by_tag(tag) -> SceneObject | None`
Returns first matching object or `None`.

## Runtime Object Lifecycle

### `self.engine.spawn(fmt, name='spawned', position=None, scale=None, color=None, tag='', scripts=None, **physics_kwargs)`
Creates an object request and queues it for end-of-frame spawn.

Supported `fmt`:
- `cube`
- `triangle`
- `light`
- model formats via scene entry semantics (`obj`, `glb`, `gltf`) when full entry fields are provided by helper paths

Example:
```python
obj = self.engine.spawn(
    "cube",
    name="crate",
    position=[0, 3, 0],
    scale=[1, 1, 1],
    color=[0.7, 0.4, 0.2],
    tag="pickup",
    scripts=["spin"],
    is_kinematic=False,
    use_gravity=True,
    mass=1.0,
    bounciness=0.2,
)
```

### `self.engine.destroy(obj)`
Queues object for removal at end-of-frame.

### `self.engine.spawn_prefab(prefab_name, position=None, tag=None, name=None)`
Instantiates object from `prefabs/<prefab_name>.json`.

### `self.engine.save_prefab(obj, prefab_name)`
Serializes object config to prefab file.

## Scene Management

### `self.engine.load_scene(scene_path)`
Fully switches scene:
- stops scripts
- resets physics
- destroys current scene meshes
- loads new scene JSON
- rebuilds renderables
- reloads scripts if currently in Play Mode

Example:
```python
self.engine.load_scene("scenes/demo.json")
```

## Audio

`self.engine.audio` is an `AudioManager`.

Common methods:
- `play_sfx(path, volume=None, loops=0)`
- `set_sfx_volume(volume)`
- `play_music(path, volume=None, loops=-1, fade_ms=0)`
- `stop_music(fade_ms=0)`
- `pause_music()`
- `resume_music()`
- `set_music_volume(volume)`
- `is_music_playing()`
- `stop_all()`

## Physics

`self.engine.physics_system` gives direct access to `PhysicsSystem` and pybullet client id.

Useful fields/methods:
- `client_id`
- `gravity`
- `set_gravity(value)`
- `collisions` (latest frame contact tuples)

`SceneObject` physics attributes often used in scripts:
- `pybullet_body_id`
- `mass`
- `is_kinematic`
- `use_gravity`
- `drag`, `friction`, `bounciness`

## Animation

If object was loaded from a skinned glTF/GLB with animation data:
- `self.entity.animator` may be available

Animator API:
- `play(name, loop=True, speed=1.0)`
- `crossfade(name, duration=0.3, loop=True, speed=1.0)`
- `stop()`
- `clip_names`
- `is_playing`

## Runtime Safety Notes

- Spawn/destroy are deferred to frame-end; avoid assuming immediate in-frame side effects.
- Always null-check optional systems:
  - `if self.entity.animator is None: ...`
  - `if self.entity.pybullet_body_id is None: ...`
- Scene loads reset many references; reacquire cached object references in `start` after scene switches.
