import pygltflib
import sys
import os

def check_animations(path):
    if not os.path.exists(path):
        print(f"Error: File not found at {path}")
        return

    try:
        gltf = pygltflib.GLTF2().load(path)
        print(f"--- Animations in {os.path.basename(path)} ---")
        if not gltf.animations:
            print("No animations found.")
        for anim in gltf.animations:
            print(f" - {anim.name}")
        print("-----------------------------------")
    except Exception as e:
        print(f"Error reading GLB: {e}")

if __name__ == "__main__":
    check_animations('assets/animations/cac2.glb')
    check_animations('assets/animations/cata_anims.glb')
