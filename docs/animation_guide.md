# BigChicken Engine: Animation Guide

This guide covers everything you need to know about the skeletal and transform animation systems in BigChicken Engine.

## 1) Importing Animations (.glb)

The engine supports skeletal animations imported from `.glb` or `.gltf` files.

1. **Model Preparation**: Use Blender to create your model and armatures.
2. **Animation Clips**: Create multiple actions in the Blender Action Editor.
3. **Export**: Export as `.glb` (Binary) with "Include -> Animation" checked.
4. **Placement**: Put the `.glb` file in `assets/models/`.
5. **Detection**: When you load the model in the engine, it automatically detects the skeleton and clips.

## 2) Playing Animations via Scripts

Attached scripts can control the `animator` component of a `SceneObject`.

```python
class MyCharacter:
    def start(self):
        if self.entity.animator:
            # List available clips
            print(f"Available: {self.entity.animator.clip_names}")
            # Play a clip immediately
            self.entity.animator.play("idle", loop=True)

    def on_event(self):
        # Smoothly transition to another clip
        self.entity.animator.crossfade("run", duration=0.2)
```

### Animator API
- `play(name, loop=True, speed=1.0)`: Instant switch.
- `crossfade(name, duration=0.3, loop=True, speed=1.0)`: Smooth blend between current and next clip.
- `stop()`: Halts playback.
- `is_playing`: Boolean property.

## 3) Automatic Animation State Controller

For characters, you can use the built-in `AnimationStateController` to handle idle/run/jump/fall transitions based on physics velocity automatically.

1. Select the character in **Dev Mode** (`F1`).
2. In the **Selected Object** panel, toggle **Anim Ctrl** to ON.
3. Set the clip names for `Idle`, `Run`, `Jump`, and `Fall`.
4. Adjust `Move Thresh` and `Vert Thresh` for sensitivities.

## 4) Creating Simple Animations in the Editor (NEW)

You can now create simple transform-based animations (moving/rotating/scaling objects) directly in the editor without external tools.

1. Select any object.
2. In the **Animation** panel:
   - Type a name for your new clip (e.g., "DoorSlide") and click **New**.
   - Move the object to its starting position -> click **Rec**.
   - Move the object to its end position -> click **Rec**.
3. **Smoothing & Timing**:
   - **Smooth Toggle**: ON = linear movement, OFF = instant jumps (step).
   - **Interval**: Time in seconds between each recorded keyframe (default: 0.5s).
4. Click **Play** to preview.
5. Click **Save** to store it in the scene.

## 5) Best Practices

- **Looping**: Ensure your "idle" and "run" clips are seamless loops in Blender.
- **Naming**: Use lowercase names for clips (`idle`, `walk`, `attack`) for easier script access.
- **Performance**: Limit the number of bones per model (Max 64 supported by default).
- **Scale**: Fix your model scale in Blender (`Ctrl+A` -> All Transforms) BEFORE exporting to avoid weird animation artifacts.
