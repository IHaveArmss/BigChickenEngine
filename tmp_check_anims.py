import sys
from pygltflib import GLTF2

def check_glb(path):
    try:
        gltf = GLTF2.load(path)
        print(f"{path}: {len(gltf.animations)} animation(s)")
        for a in gltf.animations:
            print(f"  - {a.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    for p in sys.argv[1:]:
        check_glb(p)
