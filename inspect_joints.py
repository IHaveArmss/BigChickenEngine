import os
import json
import struct

def get_joint_names(path):
    if not os.path.exists(path):
        return f"File not found: {path}"
    
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != b'glTF':
            return "Not a GLB"
        f.read(8) # version + length
        
        # Read JSON chunk
        chunk_len = struct.unpack('<I', f.read(4))[0]
        chunk_type = f.read(4)
        if chunk_type != b'JSON':
            return "No JSON chunk"
            
        json_data = json.loads(f.read(chunk_len).decode('utf-8'))
        
        nodes = json_data.get('nodes', [])
        skins = json_data.get('skins', [])
        
        if not skins:
            return "No skins found"
            
        joints = skins[0].get('joints', [])
        names = []
        for idx in joints:
            node = nodes[idx]
            names.append(node.get('name', f'node_{idx}'))
        return names

print("--- CataHobov1 ---")
print(get_joint_names(r'assets\playerModel\CataHobov1.glb'))
print("\n--- cata_formal_tpose ---")
print(get_joint_names(r'assets\animations\cata_formal_tpose.glb'))
print("\n--- Idle Animation ---")
print(get_joint_names(r'assets\animations\playerSuit\cata_formal_idle.glb'))
