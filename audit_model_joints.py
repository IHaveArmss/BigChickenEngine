import os
import sys

# Ensure current directory is in sys.path
sys.path.append(os.getcwd())

try:
    from core.model_loader import load_gltf
    path = "assets/playerModel/CataHobov1.glb"
    if os.path.exists(path):
        mesh_datas = load_gltf(path)
        # Check all meshes in the GLB for the largest joint count
        max_joints = 0
        for md in mesh_datas:
            if md.get("has_skin"):
                skeleton = md.get("skeleton")
                max_joints = max(max_joints, len(skeleton.joint_names))
        
        if max_joints > 0:
            print(f"Joint Count: {max_joints}")
        else:
            print("Model has no skin.")
    else:
        print(f"File not found: {path}")
except Exception as e:
    print(f"Error: {e}")
