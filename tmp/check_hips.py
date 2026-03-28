import sys
import os
import numpy as np
import glm

# Mocking a few classes for the script
class Channel:
    def __init__(self, bone_index, path, times, values, interpolation):
        self.bone_index = bone_index
        self.path = path
        self.times = values if isinstance(values, np.ndarray) else np.array(values, dtype='f4')
        self.values = values if isinstance(values, np.ndarray) else np.array(values, dtype='f4')
        self.interpolation = interpolation

class AnimationClip:
    def __init__(self, name, duration, channels):
        self.name = name
        self.duration = duration
        self.channels = channels

sys.path.append(os.getcwd())
from core.model_loader import load_gltf

def check():
    path = 'assets/animations/cata_anims.glb'
    print(f"\n--- Checking Hips Rotation in {path} ---")
    if not os.path.exists(path):
        print("File not found.")
        return
    
    m = load_gltf(path)
    anims = m[0].get('animations', {})
    
    run_anim = anims.get('Run')
    if not run_anim:
        print("Run animation not found.")
        return
    
    # Mixamo Hips is usually joint 32 (based on our previous check)
    # But let's find it by name in the skeleton
    skel = m[0].get('skeleton')
    hips_idx = -1
    for i, name in enumerate(skel.joint_names):
        if 'Hips' in name:
            hips_idx = i
            print(f"Hips found at local skeleton index {i} ('{name}')")
            break
            
    if hips_idx == -1:
        print("Hips bone not found in skeleton.")
        return
        
    for ch in run_anim.channels:
        if ch.bone_index == hips_idx and ch.path == 'rotation':
            # GLTF quat is [x, y, z, w]
            q_vals = ch.values[0]
            q = glm.quat(q_vals[3], q_vals[0], q_vals[1], q_vals[2])
            e = glm.degrees(glm.eulerAngles(q))
            print(f"Hips first frame rotation (Quat X,Y,Z,W): {q_vals}")
            print(f"Hips first frame rotation (Euler Degrees P,Y,R): {e}")

if __name__ == "__main__":
    check()
