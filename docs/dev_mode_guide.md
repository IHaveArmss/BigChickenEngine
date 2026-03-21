# Dev Mode Guide

This guide documents the editor workflow and all current Dev Mode UI capabilities.

## Mode Basics

- `F1`: toggle Dev Mode and Play Mode
- `F2`: toggle cursor mode and FPS mode
- `F3`: toggle hierarchy panel

Dev workflow usually looks like:
1. `F1` into Dev Mode
2. `F2` to free cursor
3. Edit scene in UI
4. `F1` into Play Mode to test
5. `F1` back to Dev Mode to iterate

## Right Panel Layout

The panel is intentionally split into:
- **Top**: scene/global controls
- **Bottom**: selected object inspector

Use mouse wheel to scroll when content exceeds panel height.

## Top Section: Scene/Global Controls

### Scene Management

- **Current**: shows active scene path
- **Scene input**: type scene name/path
- **Load**: loads scene from input
  - accepts `floor`, `floor.json`, or `scenes/floor.json`
- **Reload**: reloads current scene
- **Save Current Scene**: saves current file immediately
- **Quick Load list**: click an available scene discovered from `scenes/*.json`

### Spawn (click to place)

Spawn buttons:
- Cube
- Triangle
- Point Light

Workflow:
1. Click spawn type
2. Click viewport floor to place
3. If no floor hit is found, object spawns in front of camera

### Settings

- **Autosave** toggle (30s interval)
- **Gravity** global value (used by physics system)

### Save As

Writes a new scene file to:
- `scenes/<name>.json`

Name is sanitized to alphanumeric, `_`, `-`.

### Capabilities Quick Reference

Shows built-in control reminders directly in UI.

## Bottom Section: Selected Object Inspector

Appears when an object is selected.

### Transform

- Position (X/Y/Z)
- Rotation Euler degrees (X/Y/Z)
- Scale (X/Y/Z)

### Visual

- Color (`#RRGGBB`) for primitives/lights
- Light intensity (lights only)
- Alpha transparency (0.0 to 1.0)

### Physics

- Mass
- Bounciness
- Friction
- Drag
- Anchored (`is_kinematic`)
- Use Gravity (`use_gravity`)

### Organization

- Folder name for hierarchy grouping

### Scripts (safe add/remove flow)

Script management is explicit to avoid accidental overwrite:
1. Type one or more script names
2. Click `Add` or `Remove`
3. Confirm action

Input normalization:
- Supports commas, semicolons, and newlines
- Accepts optional `scripts/` prefix and `.py` suffix
- Automatically de-duplicates entries

## Left Panel: Hierarchy

- Folder rows can be collapsed/expanded
- Click object row to select
- `+ New Folder` creates folder
- Folder delete moves objects back to `Scene`
- Export arrow writes `exports/<folder>.obj` (non-light meshes)

## Play Mode Interaction Notes

- Physics and scripts run only in Play Mode
- Switching back to Dev Mode:
  - stops scripts
  - resets physics bodies
  - restores pre-play transforms

This lets you test gameplay without permanently drifting your authoring transforms.
