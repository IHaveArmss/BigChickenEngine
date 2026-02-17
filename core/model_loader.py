"""
OBJ + glTF model loaders.

Returns a list of MeshData dicts, each containing:
    - vertices: np.ndarray (interleaved pos+normal+uv, dtype f4)
    - indices:  np.ndarray or None (uint32)
    - color:    (r, g, b) tuple — material diffuse color
    - texture_path: str or None — path to diffuse texture image
"""

import os
import struct
import numpy as np


# ======================================================================
# OBJ Loader
# ======================================================================

def load_obj(obj_path):
    """Parse a Wavefront .obj file and its .mtl materials.
    Returns a list of MeshData dicts (one per material group)."""

    base_dir = os.path.dirname(os.path.abspath(obj_path))

    positions = []
    normals = []
    texcoords = []
    materials = {}
    current_material = None

    # Group faces by material
    face_groups = {}  # material_name -> list of face verts

    mtl_file = None

    with open(obj_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            prefix = parts[0]

            if prefix == 'mtllib':
                mtl_file = parts[1]
                materials = _parse_mtl(os.path.join(base_dir, mtl_file), base_dir)
            elif prefix == 'v':
                positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif prefix == 'vn':
                normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif prefix == 'vt':
                texcoords.append([float(parts[1]), float(parts[2])])
            elif prefix == 'usemtl':
                current_material = parts[1]
                if current_material not in face_groups:
                    face_groups[current_material] = []
            elif prefix == 'f':
                face_verts = []
                for vert_str in parts[1:]:
                    face_verts.append(_parse_face_vertex(vert_str))
                # Triangulate (fan triangulation for convex polygons)
                group = face_groups.get(current_material, [])
                if current_material not in face_groups:
                    face_groups[current_material] = group
                for i in range(1, len(face_verts) - 1):
                    group.append(face_verts[0])
                    group.append(face_verts[i])
                    group.append(face_verts[i + 1])

    # Build mesh data for each material group
    meshes = []
    for mat_name, faces in face_groups.items():
        verts = []
        for vi, vti, vni in faces:
            pos = positions[vi - 1] if vi else [0.0, 0.0, 0.0]
            norm = normals[vni - 1] if vni else [0.0, 1.0, 0.0]
            uv = texcoords[vti - 1] if vti else [0.0, 0.0]
            verts.extend(pos + norm + uv)

        mat = materials.get(mat_name, {})
        meshes.append({
            'vertices': np.array(verts, dtype='f4'),
            'indices': None,
            'color': mat.get('Kd', (0.8, 0.8, 0.8)),
            'texture_path': mat.get('map_Kd', None),
        })

    return meshes


def _parse_face_vertex(s):
    """Parse 'v', 'v/vt', 'v/vt/vn', or 'v//vn'."""
    parts = s.split('/')
    vi = int(parts[0]) if parts[0] else None
    vti = int(parts[1]) if len(parts) > 1 and parts[1] else None
    vni = int(parts[2]) if len(parts) > 2 and parts[2] else None
    return vi, vti, vni


def _parse_mtl(mtl_path, base_dir):
    """Parse a .mtl file. Returns dict of material_name -> properties."""
    materials = {}
    current = None

    if not os.path.exists(mtl_path):
        return materials

    with open(mtl_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            prefix = parts[0]

            if prefix == 'newmtl':
                current = parts[1]
                materials[current] = {}
            elif prefix == 'Kd' and current:
                materials[current]['Kd'] = (
                    float(parts[1]), float(parts[2]), float(parts[3])
                )
            elif prefix == 'map_Kd' and current:
                tex_path = ' '.join(parts[1:])
                materials[current]['map_Kd'] = os.path.join(base_dir, tex_path)

    return materials


# ======================================================================
# glTF / GLB Loader
# ======================================================================

def load_gltf(glb_path):
    """Parse a .glb file using pygltflib.
    Returns a list of MeshData dicts (one per primitive)."""
    from pygltflib import GLTF2
    import io
    from PIL import Image

    base_dir = os.path.dirname(os.path.abspath(glb_path))
    gltf = GLTF2().load(glb_path)

    # Gather all binary data blobs
    blobs = []
    # For GLB, binary blob is in gltf._glb_data or accessible via buffers
    for buf in gltf.buffers:
        if buf.uri is None:
            # Embedded GLB binary chunk
            blobs.append(gltf._glb_data if hasattr(gltf, '_glb_data') else gltf.binary_blob())
        else:
            uri_path = os.path.join(base_dir, buf.uri)
            with open(uri_path, 'rb') as f:
                blobs.append(f.read())

    def _get_accessor_data(accessor_index):
        """Read raw data from a glTF accessor."""
        accessor = gltf.accessors[accessor_index]
        buffer_view = gltf.bufferViews[accessor.bufferView]
        blob = blobs[buffer_view.buffer]

        offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
        stride = buffer_view.byteStride

        # Component type sizes
        comp_sizes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
        comp_size = comp_sizes[accessor.componentType]

        # Number of components per element
        type_counts = {
            'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4,
            'MAT2': 4, 'MAT3': 9, 'MAT4': 16,
        }
        num_components = type_counts[accessor.type]

        element_size = comp_size * num_components
        count = accessor.count

        # dtype mapping
        dtypes = {
            5120: np.int8, 5121: np.uint8, 5122: np.int16,
            5123: np.uint16, 5125: np.uint32, 5126: np.float32,
        }
        dtype = dtypes[accessor.componentType]

        if stride and stride != element_size:
            # Strided access
            data = np.zeros((count, num_components), dtype=dtype)
            for i in range(count):
                start = offset + i * stride
                chunk = blob[start:start + element_size]
                data[i] = np.frombuffer(chunk, dtype=dtype)
            return data.flatten()
        else:
            total_bytes = element_size * count
            raw = blob[offset:offset + total_bytes]
            return np.frombuffer(raw, dtype=dtype).copy()

    def _load_gltf_image(image_index):
        """Load a glTF image as a PIL Image."""
        image = gltf.images[image_index]

        if image.bufferView is not None:
            bv = gltf.bufferViews[image.bufferView]
            blob = blobs[bv.buffer]
            offset = bv.byteOffset or 0
            raw = blob[offset:offset + bv.byteLength]
            return Image.open(io.BytesIO(raw))
        elif image.uri:
            img_path = os.path.join(base_dir, image.uri)
            return Image.open(img_path)
        return None

    meshes = []

    for mesh in gltf.meshes:
        for prim in mesh.primitives:
            # Get vertex data
            pos_data = _get_accessor_data(prim.attributes.POSITION)
            positions = pos_data.reshape(-1, 3)

            if prim.attributes.NORMAL is not None:
                norm_data = _get_accessor_data(prim.attributes.NORMAL)
                normals_arr = norm_data.reshape(-1, 3)
            else:
                normals_arr = np.zeros_like(positions)
                normals_arr[:, 1] = 1.0

            if prim.attributes.TEXCOORD_0 is not None:
                uv_data = _get_accessor_data(prim.attributes.TEXCOORD_0)
                uvs = uv_data.reshape(-1, 2)
            else:
                uvs = np.zeros((len(positions), 2), dtype='f4')

            # Interleave: pos(3) + normal(3) + uv(2) = 8 floats per vertex
            vertex_data = np.hstack([
                positions.astype('f4'),
                normals_arr.astype('f4'),
                uvs.astype('f4'),
            ]).flatten()

            # Indices
            indices = None
            if prim.indices is not None:
                indices = _get_accessor_data(prim.indices).astype(np.uint32)

            # Material info
            color = (0.8, 0.8, 0.8)
            texture_image = None

            if prim.material is not None:
                material = gltf.materials[prim.material]
                pbr = material.pbrMetallicRoughness
                if pbr:
                    if pbr.baseColorFactor:
                        cf = pbr.baseColorFactor
                        color = (cf[0], cf[1], cf[2])
                    if pbr.baseColorTexture:
                        tex_index = pbr.baseColorTexture.index
                        tex = gltf.textures[tex_index]
                        if tex.source is not None:
                            pil_img = _load_gltf_image(tex.source)
                            if pil_img:
                                texture_image = pil_img

            meshes.append({
                'vertices': vertex_data,
                'indices': indices,
                'color': color,
                'texture_image': texture_image,  # PIL Image (for glTF embedded textures)
                'texture_path': None,
            })

    return meshes
