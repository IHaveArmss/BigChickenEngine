"""
OBJ + glTF model loaders.

Returns a list of MeshData dicts, each containing:
    - vertices: np.ndarray (interleaved pos+normal+uv, dtype f4)
    - indices:  np.ndarray or None (uint32)
    - color:    (r, g, b) tuple — material diffuse color
    - texture_path: str or None — path to diffuse texture image
"""

import os
import numpy as np


# Global cache to avoid redundant disk reads and GLTF parsing across the engine
_MODEL_CACHE = {}

def clear_model_cache():
    _MODEL_CACHE.clear()


# ======================================================================
# OBJ Loader
# ======================================================================

def load_obj(obj_path):
    """Parse a Wavefront .obj file and its .mtl materials.
    Returns a list of MeshData dicts (one per material group)."""
    abs_path = os.path.abspath(obj_path)
    if abs_path in _MODEL_CACHE:
        return _MODEL_CACHE[abs_path]

    base_dir = os.path.dirname(abs_path)

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

    _MODEL_CACHE[abs_path] = meshes
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

    abs_path = os.path.abspath(glb_path)
    if abs_path in _MODEL_CACHE:
        return _MODEL_CACHE[abs_path]

    base_dir = os.path.dirname(abs_path)
    gltf = GLTF2().load(abs_path)

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

        # Load base data. bufferView may be absent for sparse-only accessors
        # (base is implicitly all zeros per the glTF spec).
        if accessor.bufferView is not None:
            buffer_view = gltf.bufferViews[accessor.bufferView]
            blob = blobs[buffer_view.buffer]
            offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
            stride = buffer_view.byteStride

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
        else:
            result = np.zeros(count * num_components, dtype=dtype)

        # Apply sparse overrides. Some GLBs (e.g. Blender exports with morph
        # targets, or glTF-compressed assets) encode only the changed elements.
        if getattr(accessor, 'sparse', None) is not None:
            sparse = accessor.sparse
            sc = sparse.count

            idx_bv = gltf.bufferViews[sparse.indices.bufferView]
            idx_blob = blobs[idx_bv.buffer]
            idx_offset = (idx_bv.byteOffset or 0) + (sparse.indices.byteOffset or 0)
            idx_dtypes = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32}
            idx_dtype = idx_dtypes[sparse.indices.componentType]
            idx_elem = np.dtype(idx_dtype).itemsize
            sparse_indices = np.frombuffer(
                idx_blob[idx_offset:idx_offset + sc * idx_elem], dtype=idx_dtype).copy()

            val_bv = gltf.bufferViews[sparse.values.bufferView]
            val_blob = blobs[val_bv.buffer]
            val_offset = (val_bv.byteOffset or 0) + (sparse.values.byteOffset or 0)
            sparse_values = np.frombuffer(
                val_blob[val_offset:val_offset + sc * element_size], dtype=dtype
            ).copy().reshape(sc, num_components)

            result = result.reshape(count, num_components)
            result[sparse_indices] = sparse_values
            result = result.flatten()

        # glTF normalized integer accessors encode floats as integers:
        # UNSIGNED_BYTE 255 → 1.0, UNSIGNED_SHORT 65535 → 1.0, etc.
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

    def _compute_normals(positions, indices):
        """Compute smooth per-vertex normals by averaging adjacent face normals."""
        n = len(positions)
        normals = np.zeros((n, 3), dtype='f4')
        if indices is not None:
            tris = indices.reshape(-1, 3)
            v0 = positions[tris[:, 0]]
            v1 = positions[tris[:, 1]]
            v2 = positions[tris[:, 2]]
            face_n = np.cross(v1 - v0, v2 - v0).astype('f4')
            np.add.at(normals, tris[:, 0], face_n)
            np.add.at(normals, tris[:, 1], face_n)
            np.add.at(normals, tris[:, 2], face_n)
        else:
            for i in range(0, n - 2, 3):
                fn = np.cross(positions[i + 1] - positions[i],
                              positions[i + 2] - positions[i]).astype('f4')
                normals[i] = normals[i + 1] = normals[i + 2] = fn
        lens = np.linalg.norm(normals, axis=1, keepdims=True)
        return (normals / np.maximum(lens, 1e-8)).astype('f4')

    def _node_local_mat4(node):
        """Return the node's local transform as a 4x4 row-major numpy float32 array."""
        if node.matrix:
            # glTF stores column-major: reshape then transpose → row-major
            return np.array(node.matrix, dtype='f4').reshape(4, 4).T
        mat = np.eye(4, dtype='f4')
        if node.scale:
            mat[0, 0], mat[1, 1], mat[2, 2] = node.scale
        if node.rotation:
            x, y, z, w = node.rotation
            mat[:4, :4] = np.array([
                [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y),   0],
                [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x),   0],
                [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y), 0],
                [0,             0,              0,              1],
            ], dtype='f4') @ mat  # R * S
        if node.translation:
            T = np.eye(4, dtype='f4')
            T[0, 3], T[1, 3], T[2, 3] = node.translation
            mat = T @ mat  # T * (R * S)
        return mat

    # ---- Build node parent map ----
    parent_map = {}
    for idx, node in enumerate(gltf.nodes):
        if node.children:
            for child_idx in node.children:
                parent_map[child_idx] = idx

    # ---- Node world-transform cache (row-major numpy float32) ----
    _node_world_cache = {}

    def _node_world_mat(node_idx):
        if node_idx in _node_world_cache:
            return _node_world_cache[node_idx]
        node = gltf.nodes[node_idx]
        local = _node_local_mat4(node)
        parent_idx = parent_map.get(node_idx)
        world = (_node_world_mat(parent_idx) @ local) if parent_idx is not None else local
        _node_world_cache[node_idx] = world
        return world

    # Warm the cache for all nodes.
    for _ni in range(len(gltf.nodes)):
        _node_world_mat(_ni)

    # ---- Identify skins per mesh (fallback when no scene nodes) ----
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
            original_name = node.name or f'bone_{ji}'
            # Normalize: mixamorig:Hips -> mixamorig_Hips
            # This handles different Mixamo/Blender export naming conventions.
            norm_name = original_name.replace(':', '_').replace(' ', '_')
            joint_names.append(norm_name)

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
    # Iterate over nodes (not raw meshes) so node-level transforms are captured.
    # If multiple nodes reference the same mesh (instancing), each gets its own
    # transformed copy.  Fall back to raw mesh iteration only when the file has
    # no scene nodes at all.
    meshes = []

    node_mesh_pairs = [
        (node_idx, node.mesh, node.skin)
        for node_idx, node in enumerate(gltf.nodes)
        if node.mesh is not None
    ]
    if not node_mesh_pairs:
        node_mesh_pairs = [
            (None, mesh_idx, mesh_to_skin_idx.get(mesh_idx))
            for mesh_idx in range(len(gltf.meshes))
        ]

    _identity4 = np.eye(4, dtype='f4')

    for node_idx, mesh_idx, skin_idx in node_mesh_pairs:
        mesh = gltf.meshes[mesh_idx]
        skeleton = None
        animations = None
        if skin_idx is not None:
            skeleton, animations = _build_skeleton(skin_idx)

        # Bake this node's world transform into vertex positions/normals so the
        # existing per-object transform pipeline doesn't need to change.
        if node_idx is not None:
            world_np = _node_world_mat(node_idx)
            has_node_xform = not np.allclose(world_np, _identity4, atol=1e-6)
        else:
            world_np = _identity4
            has_node_xform = False

        for prim in mesh.primitives:
            positions = _get_accessor_data(prim.attributes.POSITION).reshape(-1, 3).astype('f4')

            # Load or compute normals.
            if prim.attributes.NORMAL is not None:
                normals_arr = _get_accessor_data(prim.attributes.NORMAL).reshape(-1, 3).astype('f4')
            else:
                # Compute smooth normals from geometry rather than defaulting to (0,1,0).
                raw_idx = None
                if prim.indices is not None:
                    raw_idx = _get_accessor_data(prim.indices).astype(np.uint32)
                normals_arr = _compute_normals(positions, raw_idx)

            # Detect if this primitive has skinning data
            prim_has_skin = False
            joints_arr = None
            weights_arr = None
            if skeleton is not None:
                j0 = getattr(prim.attributes, 'JOINTS_0', None)
                w0 = getattr(prim.attributes, 'WEIGHTS_0', None)
                if j0 is not None and w0 is not None:
                    joints_arr = _get_accessor_data(j0).astype('f4').reshape(-1, 4)
                    weights_arr = _get_accessor_data(w0).astype('f4').reshape(-1, 4)
                    prim_has_skin = True

            # Apply the node's world transform into vertex data.
            # IMPORTANT: We skip this for skinned primitives because the skeleton
            # already handles the world-space placement from the bind pose.
            if has_node_xform and not prim_has_skin:
                M33 = world_np[:3, :3]
                pos_h = np.hstack([positions, np.ones((len(positions), 1), dtype='f4')])
                positions = (pos_h @ world_np.T)[:, :3].astype('f4')
                try:
                    normals_arr = (normals_arr @ np.linalg.inv(M33)).astype('f4')
                    lens = np.linalg.norm(normals_arr, axis=1, keepdims=True)
                    normals_arr = normals_arr / np.maximum(lens, 1e-8)
                except np.linalg.LinAlgError:
                    pass

            if prim.attributes.TEXCOORD_0 is not None:
                uvs = _get_accessor_data(prim.attributes.TEXCOORD_0).reshape(-1, 2).astype('f4')
            else:
                uvs = np.zeros((len(positions), 2), dtype='f4')

            if prim_has_skin:
                vertex_data = np.hstack([
                    positions,
                    normals_arr,
                    uvs,
                    joints_arr,
                    weights_arr,
                ]).flatten()
            else:
                vertex_data = np.hstack([positions, normals_arr, uvs]).flatten()

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
                'collision_verts': positions,
                'indices': indices,
                'color': color,
                'texture_image': texture_image,
                'texture_path': None,
                'has_skin': prim_has_skin,
            }
            if prim_has_skin:
                md['skeleton'] = skeleton
                md['animations'] = animations

            meshes.append(md)

    _MODEL_CACHE[abs_path] = meshes
    return meshes
