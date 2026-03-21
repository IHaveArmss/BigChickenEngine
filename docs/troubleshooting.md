# Troubleshooting

## Engine Fails to Launch

### Symptom
- Window does not open, or exits immediately.

### Checks
- Confirm Python version is 3.10+
- Reinstall deps:
  - `pip install -r requirements.txt`
- Verify OpenGL 3.3+ support and updated GPU drivers

## Script Not Running

### Symptom
- Attached script does not print/log or affect object in Play Mode.

### Checks
1. Ensure you are in Play Mode (`F1` from Dev Mode).
2. In Selected Object -> Scripts, verify script appears under `Attached`.
3. Check script class naming:
   - `my_script.py` expects `MyScript` or fallback `Script`.
4. Check console output for ScriptManager warnings/errors.

## Multiple Scripts Not Working

### Symptom
- Only one script appears active.

### Correct Flow
1. Type script names in Scripts input (`camera_follow, spawn_destroy_test`)
2. Click `Add`
3. Click `Confirm`
4. Verify both show under `Attached`

If still failing, check console for missing file warnings.

## Object Falls in Editor

### Expected Behavior
- Physics runs only in Play Mode.

If you observe drift:
- Confirm mode/title indicates Dev Mode
- Toggle `F1` twice to force script/physics reset

## Object Does Not Fall in Play Mode

### Checks
- `Anchored` (`is_kinematic`) must be OFF
- `Use Gravity` must be ON
- `Mass` must be > 0

## Scene Load/Reload Not Working

### Checks
- Use valid scene path/name:
  - `demo`
  - `demo.json`
  - `scenes/demo.json`
- Confirm file exists under `scenes/`
- Check console warnings for not found path

## Audio Not Playing

### Checks
- Verify file exists:
  - `assets/audio/music.ogg`
  - `assets/audio/sfx.wav`
- Confirm no warning:
  - `[Audio] WARNING: ... not found`
- Confirm system audio output device is available

## Model Not Appearing

### Checks
- Verify `model` path exists in scene JSON
- Confirm `format` matches file type (`obj`, `glb`, `gltf`)
- Check console for scene loader warnings

## Animation Not Playing

### Checks
- Model must include skin + animation clips in glTF/GLB
- `SceneObject.animator` exists only when skin/animation were parsed
- Use script checks:
  - `if self.entity.animator: ...`

## Save/Autosave Confusion

- **Save Current Scene** and `Ctrl+S` write to current scene path.
- **Save As** writes a new file and makes it current.
- Autosave runs only in Dev Mode and uses current scene path.

## Where to Look Next

- `docs/dev_mode_guide.md`
- `docs/scripting_guide.md`
- `docs/scene_format_reference.md`
- `docs/engine_runtime_api.md`
- `docs/engine_architecture.md`
