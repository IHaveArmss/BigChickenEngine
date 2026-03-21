# Getting Started

This guide gets you from a fresh checkout to editing a scene, attaching scripts, and testing gameplay.

## 1) Install and Run

```bash
pip install -r requirements.txt
python main.py
```

Requirements:
- Python 3.10+
- OpenGL 3.3+ compatible GPU/driver

## 2) Understand the Two Modes

- **Dev Mode** (`F1`): scene editing tools and UI
- **Play Mode** (`F1` again): physics simulation and scripts run

Use `F2` to switch between:
- Cursor mode (interact with UI)
- FPS mode (mouse-look camera movement)

## 3) First Scene Edit

1. Press `F1` (enter Dev Mode), then `F2` to free cursor.
2. In right panel top section, click `Cube` in **Spawn**.
3. Click viewport to place the cube.
4. Select the cube in viewport or hierarchy.
5. In **Selected Object** section, edit position/scale/color.
6. Press `Ctrl+S` or click **Save Current Scene**.

## 4) Attach and Test a Script

1. Select object.
2. In **Selected Object -> Scripts**, type:
   - `spawn_destroy_test`
3. Click `Add`, then `Confirm`.
4. Press `F1` to enter Play Mode.
5. Press `F` to spawn cubes, `X` to destroy tagged objects.

You can attach multiple scripts by entering several names:
- `camera_follow, spawn_destroy_test`

## 5) Scene Management Workflow

In the top **Scene Management** section:
- Enter `demo` and click `Load` to load `scenes/demo.json`
- Click `Reload` to reload current scene file
- Use quick scene buttons to switch fast
- Use **Save Current Scene** for immediate save
- Use **Save As** to write a new scene file

## 6) Common Controls

- `F1`: Dev/Play toggle
- `F2`: Cursor/FPS toggle
- `F3`: Hierarchy panel toggle
- `W/A/S/D`, mouse: FPS camera
- `Delete`: delete selected object
- `Ctrl+S`: save current scene

## 7) Next Steps

- Read `docs/dev_mode_guide.md` for full editor workflow
- Read `docs/scripting_guide.md` for script lifecycle and examples
- Read `docs/animation_guide.md` for our new animation recording system
- Read `docs/scene_format_reference.md` to hand-edit scene JSON safely
- Read `docs/engine_architecture.md` for subsystem internals
