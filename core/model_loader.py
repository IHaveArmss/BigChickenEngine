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
    """Parse a .glb/.gltf file using pygltflib.
    Returns a list of MeshData dicts (one per primitive).
    If the model has skeletal animation, each dict includes
    'has_skin', 'skeleton', and 'animations' keys."""
    from pygltflib import GLTF2
    import io
    from PIL import Image
    import glm as _glm
    from core.animator import Skeleton, AnimationClip, Channel

    base_dir = os.path.dirname(os.path.abspath(glb_path))
    gltf = GLTF2().load(glb_path)

    blobs = []
    for buf in gltf.buffers:
        if buf.uri is None:
            blobs.append(gltf._glb_data if hasattr(gltf, '_glb_data') else gltf.binary_blob())
        else:
            uri_path = os.path.join(base_dir, buf.uri)
            with open(uri_path, 'rb') as f:
                blobs.append(f.read())

    def _get_accessor_data(accessor_index):
        accessor = gltf.accessors[accessor_index]
        buffer_view = gltf.bufferViews[accessor.bufferView]
        blob = blobs[buffer_view.buffer]
        offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
        stride = buffer_view.byteStride
        comp_sizes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
        comp_size = comp_sizes[accessor.componentType]
        type_counts = {
            'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4,
            'MAT2': 4, 'MAT3': 9, 'MAT4': 16,
        }
        num_components = type_counts[accessor.type]
        element_size = comp_size * num_components
        count = accessor.count
        dtypes = {
            5120: np.int8, 5121: np.uint8, 5122: np.int16,
            5123: np.uint16, 5125: np.uint32, 5126: np.float32,
        }
        dtype = dtypes[accessor.componentType]

        if stride and stride != element_size:
            data = np.zeros((count, num_components), dtype=dtype)
            for i in range(count):
                start = offset + i * stride
                chunk = blob[start:start + element_size]
                data[i] = np.frombuffer(chunk, dtype=dtype)
            result = data.flatten()
        else:
            total_bytes = element_size * count
            raw = blob[offset:offset + total_bytes]
            result = np.frombuffer(raw, dtype=dtype).copy()

        # glTF normalized integer accessors encode floats as integers:
        # UNSIGNED_BYTE 255 → 1.0, UNSIGNED_SHORT 65535 → 1.0, etc.
        # Convert to float32 now so callers always get the true numeric values.
        if getattr(accessor, 'normalized', False) and dtype != np.float32:
            _norm_max = {np.int8: 127.0, np.uint8: 255.0,
                         np.int16: 32767.0, np.uint16: 65535.0}
            divisor = _norm_max.get(dtype, 1.0)
            result = result.astype(np.float32) / divisor

        return result

    def _load_gltf_image(image_index):
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

    # ---- Build node parent map ----
    parent_map = {}
    for idx, node in enumerate(gltf.nodes):
        if node.children:
            for child_idx in node.children:
                parent_map[child_idx] = idx

    # ---- Identify skins per mesh ----
    mesh_to_skin_idx = {}
    for node in gltf.nodes:
        if node.mesh is not None and node.skin is not None:
            mesh_to_skin_idx[node.mesh] = node.skin

    # ---- Pre-build skeleton + animations per skin ----
    skin_cache = {}

    def _build_skeleton(skin_idx):
        if skin_idx in skin_cache:
            return skin_cache[skin_idx]

        skin = gltf.skins[skin_idx]
        joint_nodes = skin.joints
        num_joints = len(joint_nodes)
        node_to_joint = {n: j for j, n in enumerate(joint_nodes)}

        joint_names = []
        parent_indices = []
        bind_translations = []
        bind_rotations = []
        bind_scales = []

        for ji, ni in enumerate(joint_nodes):
            node = gltf.nodes[ni]
            joint_names.append(node.name or f'bone_{ji}')

            p_node = parent_map.get(ni)
            parent_indices.append(node_to_joint.get(p_node, -1) if p_node is not None else -1)

            if node.translation:
                bind_translations.append(_glm.vec3(*node.translation))
            else:
                bind_translations.append(_glm.vec3(0.0))

            if node.rotation:
                r = node.rotation
                bind_rotations.append(_glm.quat(r[3], r[0], r[1], r[2]))
            else:
                bind_rotations.append(_glm.quat(1.0, 0.0, 0.0, 0.0))

            if node.scale:
                bind_scales.append(_glm.vec3(*node.scale))
            else:
                bind_scales.append(_glm.vec3(1.0))

        ibm_list = []
        if skin.inverseBindMatrices is not None:
            ibm_data = _get_accessor_data(skin.inverseBindMatrices).astype(np.float32)
            ibm_flat = ibm_data.reshape(num_joints, 16)
            for row in ibm_flat:
                cols = [_glm.vec4(row[0], row[1], row[2], row[3]),
                        _glm.vec4(row[4], row[5], row[6], row[7]),
                        _glm.vec4(row[8], row[9], row[10], row[11]),
                        _glm.vec4(row[12], row[13], row[14], row[15])]
                ibm_list.append(_glm.mat4(*cols))
        else:
            ibm_list = [_glm.mat4(1.0)] * num_joints

        skeleton = Skeleton(
            joint_names, parent_indices, ibm_list,
            bind_translations, bind_rotations, bind_scales,
        )

        animations = {}
        if gltf.animations:
            for anim in gltf.animations:
                channels = []
                for ch in anim.channels:
                    target_node = ch.target.node
                    if target_node not in node_to_joint:
                        continue
                    bone_idx = node_to_joint[target_node]
                    path = ch.target.path

                    sampler = anim.samplers[ch.sampler]
                    times = _get_accessor_data(sampler.input).astype(np.float32)
                    raw_values = _get_accessor_data(sampler.output).astype(np.float32)

                    parsed_values = []
                    if path == 'translation' or path == 'scale':
                        arr = raw_values.reshape(-1, 3)
                        for v in arr:
                            parsed_values.append(_glm.vec3(float(v[0]), float(v[1]), float(v[2])))
                    elif path == 'rotation':
                        arr = raw_values.reshape(-1, 4)
                        for v in arr:
                            parsed_values.append(_glm.quat(float(v[3]), float(v[0]), float(v[1]), float(v[2])))
                    else:
                        continue

                    interp = getattr(sampler, 'interpolation', 'LINEAR') or 'LINEAR'
                    channels.append(Channel(bone_idx, path, times, parsed_values, interp))

                duration = 0.0
                for c in channels:
                    if len(c.times) > 0:
                        duration = max(duration, float(c.times[-1]))

                clip_name = anim.name or f'animation_{len(animations)}'
                animations[clip_name] = AnimationClip(clip_name, duration, channels)

        skin_cache[skin_idx] = (skeleton, animations)
        return skeleton, animations

    # ---- Build meshes ----
    meshes = []

    for mesh_idx, mesh in enumerate(gltf.meshes):
        skin_idx = mesh_to_skin_idx.get(mesh_idx)
        skeleton = None
        animations = None
        if skin_idx is not None:
            skeleton, animations = _build_skeleton(skin_idx)

        for prim in mesh.primitives:
            pos_data = _get_accessor_data(prim.attributes.POSITION)
            positions = pos_data.reshape(-1, 3)

            if prim.attributes.NORMAL is not None:
                normals_arr = _get_accessor_data(prim.attributes.NORMAL).reshape(-1, 3)
            else:
                normals_arr = np.zeros_like(positions)
                normals_arr[:, 1] = 1.0

            if prim.attributes.TEXCOORD_0 is not None:
                uvs = _get_accessor_data(prim.attributes.TEXCOORD_0).reshape(-1, 2)
            else:
                uvs = np.zeros((len(positions), 2), dtype='f4')

            has_skin = False
            joints_arr = None
            weights_arr = None

            if skeleton is not None:
                j0 = getattr(prim.attributes, 'JOINTS_0', None)
                w0 = getattr(prim.attributes, 'WEIGHTS_0', None)
                if j0 is not None and w0 is not None:
                    joints_arr = _get_accessor_data(j0).astype('f4').reshape(-1, 4)
                    weights_arr = _get_accessor_data(w0).astype('f4').reshape(-1, 4)
                    has_skin = True

            if has_skin:
                vertex_data = np.hstack([
                    positions.astype('f4'),
                    normals_arr.astype('f4'),
                    uvs.astype('f4'),
                    joints_arr,
                    weights_arr,
                ]).flatten()
            else:
                vertex_data = np.hstack([
                    positions.astype('f4'),
                    normals_arr.astype('f4'),
                    uvs.astype('f4'),
                ]).flatten()

            indices = None
            if prim.indices is not None:
                indices = _get_accessor_data(prim.indices).astype(np.uint32)

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

            md = {
                'vertices': vertex_data,
                'indices': indices,
                'color': color,
                'texture_image': texture_image,
                'texture_path': None,
                'has_skin': has_skin,
            }
            if has_skin:
                md['skeleton'] = skeleton
                md['animations'] = animations

            meshes.append(md)

    return meshes
