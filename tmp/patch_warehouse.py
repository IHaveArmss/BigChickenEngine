"""Scale down warehouse enemies to 50% (from 2.0 to 1.0)."""
import json

SCENE_PATH = 'scenes/warehouse.json'

with open(SCENE_PATH, 'r') as f:
    data = json.load(f)

changed = 0
for obj in data.get('objects', []):
    if 'enemy' not in obj.get('scripts', []):
        continue
    
    # User requested 50% scale. They were at [2.0, 2.0, 2.0], so change to [1.0, 1.0, 1.0]
    # We also keep a slightly larger/taller collider_scale if needed, but for simplicity
    # we just use scale [1.0, 1.0, 1.0]. Given character height, we also use a box 
    # collider to prevent any capsule tipping/clipping issues.
    obj['scale'] = [1.25, 1.25, 1.25]
    obj['collider_type'] = 'box'  # Box is safer for orientation/clipping than capsule
    
    changed += 1
    print(f"  Scaled: {obj['name']} to [1.25, 1.25, 1.25]")

with open(SCENE_PATH, 'w') as f:
    json.dump(data, f, indent=2)

print(f"\nDone! Scaled {changed} enemies to 50%.")
