import sys
import os
import numpy as np
import glm

sys.path.append(os.getcwd())
from core.model_loader import load_gltf

def check():
    path = 'assets/playerModel/CataHobov1.glb'
    print(f"\n--- Checking Base Model Hips in {path} ---")
    if not os.path.exists(path):
        print("File not found.")
        return
    
    m = load_gltf(path)
    skel = m[0].get('skeleton')
    if not skel:
        print("No skeleton found.")
        return
        
    hips_idx = -1
    for i, name in enumerate(skel.joint_names):
        if 'Hips' in name:
            hips_idx = i
            print(f"Hips found at local skeleton index {i} ('{name}')")
            break
            
    if hips_idx == -1:
        print("Hips bone not found.")
        return
        
    q = skel.bind_rotations[hips_idx]
    e = glm.degrees(glm.eulerAngles(q))
    print(f"Base Hips Bind Rotation (Quat X,Y,Z,W): {q.x}, {q.y}, {q.z}, {q.w}")
    print(f"Base Hips Bind Rotation (Euler Degrees P,Y,R): {e}")

if __name__ == "__main__":
    check()
