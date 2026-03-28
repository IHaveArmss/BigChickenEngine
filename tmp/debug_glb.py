import sys
import os
from pygltflib import GLTF2

def debug_glb(path):
    print(f"\n--- Hierarchy Debug for {path} ---")
    if not os.path.exists(path):
        print("File not found.")
        return
    
    gltf = GLTF2.load(path)
    
    # Map nodes to parents
    parent_map = {}
    for i, node in enumerate(gltf.nodes):
        for child in node.children:
            parent_map[child] = i

    # Trace parents of first joint
    if gltf.skins:
        skin = gltf.skins[0]
        first_joint_idx = skin.joints[0]
        
        print(f"Tracing parents of joint {first_joint_idx} ('{gltf.nodes[first_joint_idx].name}'):")
        curr = first_joint_idx
        while curr in parent_map:
            parent_idx = parent_map[curr]
            p_node = gltf.nodes[parent_idx]
            print(f"  <- Parent Node {parent_idx} ('{p_node.name}'): T={p_node.translation} R={p_node.rotation} S={p_node.scale}")
            curr = parent_idx
    else:
        # Check all nodes for rotations
        for i, node in enumerate(gltf.nodes):
            if node.rotation or node.scale or node.translation:
                print(f"Node {i} ('{node.name}'): T={node.translation} R={node.rotation} S={node.scale}")

if __name__ == "__main__":
    debug_glb('assets/playerModel/CataHobov1.glb')
    debug_glb('assets/animations/cata_anims.glb')
