"""OBJ Exporter — combines scene objects in a folder into a single .obj file."""

import os
import struct
import numpy as np
from pyglm import glm


def export_folder_to_obj(folder_name, scene_objects, output_dir='exports'):
    """Export all non-light objects in *folder_name* to a single .obj file.

    Each object becomes a named group (``o <name>``) so Blender shows them
    separately.  Vertex positions and normals are transformed to world space
    using each mesh's model matrix.

    Returns the absolute path to the written file, or None on failure.
    """

    # Collect objects belonging to this folder
    folder_objects = [
        obj for obj in scene_objects
        if getattr(obj, 'folder', 'Scene') == folder_name and not obj.is_light
    ]

    if not folder_objects:
        print(f"[Export] No exportable objects in folder '{folder_name}'")
        return None

    os.makedirs(output_dir, exist_ok=True)

    safe_name = folder_name.replace(' ', '_').replace('/', '_')
    out_path = os.path.join(output_dir, f'{safe_name}.obj')

    # Global counters — OBJ indices are 1-based and cumulative across groups
    v_offset = 1
    vn_offset = 1
    vt_offset = 1

    lines = [
        f'# BigChicken Engine — exported folder "{folder_name}"',
        f'# Objects: {len(folder_objects)}',
        '',
    ]

    for obj in folder_objects:
        lines.append(f'o {obj.name}')

        for mesh in obj.meshes:
            positions, normals, uvs, faces = _extract_mesh_data(mesh)

            if positions is None:
                continue

            num_verts = len(positions)

            # Write vertices
            for p in positions:
                lines.append(f'v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}')

            # Write normals
            for n in normals:
                lines.append(f'vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}')

            # Write UVs
            for uv in uvs:
                lines.append(f'vt {uv[0]:.6f} {uv[1]:.6f}')

            # Write faces (triangles)
            for i in range(0, len(faces), 3):
                i0 = faces[i] + v_offset
                i1 = faces[i + 1] + v_offset
                i2 = faces[i + 2] + v_offset
                # OBJ face format: v/vt/vn
                f0 = f'{i0}/{faces[i] + vt_offset}/{faces[i] + vn_offset}'
                f1 = f'{i1}/{faces[i+1] + vt_offset}/{faces[i+1] + vn_offset}'
                f2 = f'{i2}/{faces[i+2] + vt_offset}/{faces[i+2] + vn_offset}'
                lines.append(f'f {f0} {f1} {f2}')

            v_offset += num_verts
            vn_offset += num_verts
            vt_offset += num_verts

        lines.append('')

    with open(out_path, 'w') as f:
        f.write('\n'.join(lines))

    abs_path = os.path.abspath(out_path)
    print(f'[Export] Saved: {abs_path}  ({len(folder_objects)} objects)')
    return abs_path


def _extract_mesh_data(mesh):
    """Read vertex data from a mesh's GPU buffer and apply its world transform.

    Returns (positions, normals, uvs, face_indices) or (None,)*4 on failure.
    Each array uses numpy; face_indices is a flat list of triangle vertex indices.
    """

    try:
        raw_bytes = mesh.vbo.read()
    except Exception as e:
        print(f'[Export] Could not read VBO: {e}')
        return None, None, None, None

    # Determine vertex stride
    # Standard meshes: pos(3) + norm(3) + uv(2) = 8 floats = 32 bytes
    # LightOrb (unlit): pos(3) only = 3 floats = 12 bytes — skip these
    float_count = len(raw_bytes) // 4
    total_floats = np.frombuffer(raw_bytes, dtype=np.float32)

    # Detect stride
    if float_count % 8 == 0:
        stride = 8
    elif float_count % 3 == 0:
        # Probably pos-only (LightOrb) — not useful for export
        return None, None, None, None
    else:
        print(f'[Export] Unknown vertex layout ({float_count} floats)')
        return None, None, None, None

    num_verts = float_count // stride
    data = total_floats.reshape(num_verts, stride)

    local_positions = data[:, 0:3].copy()
    local_normals = data[:, 3:6].copy()
    uvs = data[:, 6:8].copy()

    # Apply model matrix (world transform)
    model = mesh.transform.model_matrix()
    # Normal matrix = transpose(inverse(model_mat3))
    model_mat3 = glm.mat3(model)
    normal_mat = glm.transpose(glm.inverse(model_mat3))

    positions = np.zeros_like(local_positions)
    normals = np.zeros_like(local_normals)

    for i in range(num_verts):
        # Transform position
        p = glm.vec3(float(local_positions[i, 0]),
                     float(local_positions[i, 1]),
                     float(local_positions[i, 2]))
        wp = glm.vec3(model * glm.vec4(p, 1.0))
        positions[i] = [wp.x, wp.y, wp.z]

        # Transform normal
        n = glm.vec3(float(local_normals[i, 0]),
                     float(local_normals[i, 1]),
                     float(local_normals[i, 2]))
        wn = glm.normalize(normal_mat * n)
        normals[i] = [wn.x, wn.y, wn.z]

    # Build face indices
    index_buf = getattr(mesh, '_index_buffer', None)
    if index_buf is not None:
        try:
            idx_bytes = index_buf.read()
            faces = np.frombuffer(idx_bytes, dtype=np.uint32).tolist()
        except Exception:
            faces = list(range(num_verts))
    else:
        faces = list(range(num_verts))

    return positions, normals, uvs, faces
