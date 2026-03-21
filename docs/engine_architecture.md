# Engine Architecture Guide

This document explains how the engine is structured, how frame execution works, and how systems interact.

## 1) High-Level Design

The engine is centered around `GraphicsEngine` in `engine.py`.

Primary responsibilities:
- Initialize window, OpenGL context, cameras, and subsystems
- Load scenes and maintain object/renderable collections
- Process input, update gameplay systems, and render each frame
- Manage Dev Mode/Play Mode transitions

Core subsystems:
- Rendering (`core/renderer.py`, mesh/shader classes)
- Physics (`core/physics_system.py`)
- Scripting (`core/script_manager.py`)
- Scene serialization/loading (`core/scene_loader.py`)
- Audio (`core/audio_manager.py`)
- UI/editor tools (`core/editor_ui.py`, `core/dev_mode.py`, `core/scene_hierarchy.py`)
- Prefabs (`core/prefab_manager.py`)
- Animation (`core/animator.py`, model loader/skinning path)

## 2) Data Model

### `SceneObject`
Defined in `core/scene_loader.py`. It groups one logical object and one-or-more render meshes.

Key fields:
- Identity: `name`, `format`, `model_path`
- Rendering: `meshes`, `alpha`, (light fields when applicable)
- Organization: `folder`, `tag`
- Script binding: `scripts`
- Physics: `mass`, `is_kinematic`, `use_gravity`, `friction`, `bounciness`, `drag`, `collider_type`
- Runtime: `pybullet_body_id`, `animator`, `_physics_dirty`

`position`, `scale`, and rotation helpers proxy to all meshes in the object.

## 3) Frame Pipeline

Main loop:
1. Input (`InputHandler.process_events`)
2. Update (`GraphicsEngine.update`)
3. Render (`GraphicsEngine.render`)

### Update (important order)

Within `GraphicsEngine.update`:
1. Camera movement when in FPS mode
2. Dev transform manipulation (if editing selected object in FPS mode)
3. Apply editor UI property values (in cursor mode)
4. Autosave (Dev Mode only)
5. Play Mode simulation:
   - `physics_system.step(dt, scene_objects)` returns number of fixed substeps
   - `script_manager.fixed_update_all(FIXED_TIMESTEP)` once per substep
   - `script_manager.dispatch_collisions(...)`
   - `script_manager.update_all(dt)`
6. Update UI/hierarchy states
7. Update renderables and animators
8. Flush deferred spawn/destroy queues

### Render

`Renderer.render`:
- Clears frame
- Builds light list (global orbit + scene light objects)
- Computes view-projection frustum planes
- Frustum-culls using bounding sphere test
- Draws opaque objects
- Draws transparent objects back-to-front (alpha correct)
- Draws selected wireframe highlight in Dev Mode
- Draws HUD/UI

## 4) Mode Switching

`toggle_dev_mode` is a key state transition:

To Play Mode:
- Applies pending UI object changes
- Snapshots transforms for restore
- Loads scripts

Back to Dev Mode:
- Stops scripts (`stop_all`)
- Resets physics world
- Restores snapshot transforms

This prevents editor state pollution from gameplay simulation.

## 5) Physics System

`PhysicsSystem` uses pybullet in `DIRECT` mode.

Characteristics:
- Fixed timestep accumulator (`1/240`) with `MAX_SUBSTEPS` cap
- Dynamic body registration from `scene_objects`
- Dirty-state sync for transform edits
- Scale-change body rebuild
- Dynamics caching to avoid repeated expensive `changeDynamics` calls
- Optional per-object gravity override (`use_gravity`)
- Collision collection each stepped frame
- Post-step drag and transform sync back into scene objects

Collision events are later forwarded by `ScriptManager`.

## 6) Script System

`ScriptManager` flow:
- Normalize script names (`scripts/` and `.py` optional)
- Dynamic import from `scripts/`
- Resolve class name by file-name PascalCase or fallback `Script`
- Inject `engine` and `entity`
- Call lifecycle callbacks with robust exception handling
- Remove loaded script modules from `sys.modules` on stop to avoid stale code reuse

## 7) Scene Loading and Saving

`load_scene`:
- Parses scene JSON
- Creates each object via `spawn_from_entry`
- Handles primitives and model formats
- For skinned models: creates `Animator`, links it to skinned meshes, auto-plays first clip

`save_scene`:
- Serializes current object transforms and properties
- Preserves tag/scripts/folder and format-specific fields

## 8) Runtime Spawn/Destroy and Prefabs

Engine runtime API queues spawn/destroy operations:
- `_pending_spawns`
- `_pending_destroys`

Applied in `_flush_spawn_destroy` at end of frame to avoid mutating scene lists while systems iterate.

Prefabs:
- `save_prefab` serializes one object
- `load_prefab` reads prefab dict
- `spawn_prefab` instantiates prefab via same scene-entry spawn path

## 9) Animation Pipeline

Skinned model path:
1. glTF loader extracts:
   - skeleton hierarchy
   - inverse bind matrices
   - animation channels/clips
   - vertex joints/weights
2. `Animator` samples clips and builds bone matrices per frame
3. `ModelMesh` uploads bone matrices to `phong_skinned.vert`
4. Vertex shader applies linear blend skinning

Supports:
- clip play
- loop control
- speed control
- crossfade blending

## 10) Editor UI and Hierarchy

Right panel (`EditorUI`):
- Scene/global controls at top
- Selected object inspector at bottom
- Explicit script add/remove with confirmation
- Scrollable content

Left panel (`SceneHierarchy`):
- Folder tree view
- Selection
- Folder create/delete
- Folder export to OBJ

## 11) Extension Guidelines

When adding systems:
- Integrate into `GraphicsEngine.update` with clear ordering
- Keep scene mutations deferred if iterated elsewhere in same frame
- Preserve mode semantics (Dev Mode should remain non-simulating)
- Keep script callbacks fault-tolerant
- Document new user-facing controls and API in `docs/`
