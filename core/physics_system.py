import pybullet as p
import pybullet_data
import glm
import numpy as np
import os

FIXED_TIMESTEP = 1.0 / 240.0
MAX_SUBSTEPS = 10
AIR_RESISTANCE_STRENGTH = 5.0


class CollisionInfo:
    """Lightweight data passed to script on_collision callbacks."""
    __slots__ = ('other', 'point', 'normal', 'impulse')

    def __init__(self, other, point, normal, impulse):
        self.other = other
        self.point = point
        self.normal = normal
        self.impulse = impulse


class PhysicsSystem:
    def __init__(self, gravity=-9.81):
        self.client_id = p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())

        self.gravity = gravity
        p.setGravity(0, self.gravity, 0, physicsClientId=self.client_id)
        p.setPhysicsEngineParameter(
            fixedTimeStep=FIXED_TIMESTEP,
            numSubSteps=1,
            physicsClientId=self.client_id,
        )

        self.body_map = {}
        self.body_scales = {}
        self._cached_dynamics = {}
        self._body_to_obj = {}
        self._time_accumulator = 0.0
        self.collisions = []

    def set_gravity(self, new_gravity):
        """Update the global physical gravity."""
        if self.gravity != new_gravity:
            self.gravity = new_gravity
            p.setGravity(0, self.gravity, 0, physicsClientId=self.client_id)

            for body_id in self.body_map.values():
                p.changeDynamics(body_id, -1, activationState=p.ACTIVATION_STATE_WAKE_UP,
                                 physicsClientId=self.client_id)

    def _extract_scale(self, obj):
        """Return the scale used for collision shape sizing.
        If the object has a 'collider_scale' override, that is used instead
        of the visual transform scale, allowing small-scale models to have
        a properly-sized physics collider."""
        cs = getattr(obj, 'collider_scale', None)
        if cs is not None:
            # collider_scale is stored as a list [sx, sy, sz]
            if isinstance(cs, (list, tuple)) and len(cs) >= 3:
                return float(cs[0]), float(cs[1]), float(cs[2])
            if hasattr(cs, 'x'):
                return float(cs.x), float(cs.y), float(cs.z)
        s = obj.scale
        return (s.x if hasattr(s, 'x') else s[0],
                s.y if hasattr(s, 'y') else s[1],
                s.z if hasattr(s, 'z') else s[2])

    def _extract_offset(self, obj):
        """Return the local-space collider offset as a glm.vec3."""
        co = getattr(obj, 'collider_offset', None)
        if co is None:
            return glm.vec3(0.0)
        if isinstance(co, (list, tuple)):
            if len(co) >= 3:
                return glm.vec3(float(co[0]), float(co[1]), float(co[2]))
            return glm.vec3(0.0)
        if hasattr(co, 'x'):
            return glm.vec3(float(co.x), float(co.y), float(co.z))
        return glm.vec3(0.0)

    def _offset_world(self, obj, quat=None):
        """Rotate the collider offset into world space."""
        offset = self._extract_offset(obj)
        if glm.length(offset) < 1e-8:
            return glm.vec3(0.0)
        if quat is None:
            rotation = obj.rotation
        else:
            rotation = glm.quat(quat[3], quat[0], quat[1], quat[2])
        return rotation * offset

    def _dynamics_key(self, obj):
        """Return a hashable snapshot of the physics-relevant properties."""
        is_kin = getattr(obj, 'is_kinematic', True)
        mass = 0.0 if is_kin else getattr(obj, 'mass', 1.0)
        return (mass,
                getattr(obj, 'bounciness', 0.0),
                getattr(obj, 'friction', 0.5),
                getattr(obj, 'drag', 0.02),
                getattr(obj, 'use_gravity', False))

    def _safe_extent(self, value):
        try:
            return max(abs(float(value)), 1e-4)
        except Exception:
            return 1e-4

    def _create_box_shape(self, sx, sy, sz):
        return p.createCollisionShape(
            p.GEOM_BOX,
            halfExtents=[self._safe_extent(sx) * 0.5,
                         self._safe_extent(sy) * 0.5,
                         self._safe_extent(sz) * 0.5],
            physicsClientId=self.client_id,
        )

    def add_object(self, obj):
        """Register a SceneObject into the PyBullet world."""
        if not getattr(obj, 'is_collideable', True):
            return

        is_kinematic = getattr(obj, 'is_kinematic', True)
        mass = 0.0 if is_kinematic else getattr(obj, 'mass', 1.0)
        bounciness = getattr(obj, 'bounciness', 0.0)
        friction = getattr(obj, 'friction', 0.5)
        drag = getattr(obj, 'drag', 0.02)

        col_type = getattr(obj, 'collider_type', 'box')
        sx, sy, sz = self._extract_scale(obj)

        shape_ids = []
        if col_type == 'box':
            try:
                shape_ids.append(self._create_box_shape(sx, sy, sz))
            except Exception as e:
                print(f"[Physics] WARNING: Box collider failed for {obj.name}, falling back to unit box: {e}")
                shape_ids.append(self._create_box_shape(1.0, 1.0, 1.0))
        elif col_type == 'sphere':
            try:
                shape_ids.append(p.createCollisionShape(
                    p.GEOM_SPHERE, radius=max(self._safe_extent(sx), self._safe_extent(sy), self._safe_extent(sz)) * 0.5,
                    physicsClientId=self.client_id))
            except Exception as e:
                print(f"[Physics] WARNING: Sphere collider failed for {obj.name}, falling back to unit box: {e}")
                shape_ids.append(self._create_box_shape(1.0, 1.0, 1.0))
        elif col_type == 'capsule':
            radius = max(min(self._safe_extent(sx), self._safe_extent(sz)) * 0.35, 1e-4)
            cyl_h  = max(self._safe_extent(sy) - radius * 2.0, 1e-4)
            try:
                shape_ids.append(p.createCollisionShape(
                    p.GEOM_CAPSULE, radius=radius, height=cyl_h,
                    physicsClientId=self.client_id))
            except Exception as e:
                print(f"[Physics] WARNING: Capsule collider failed for {obj.name}, falling back to unit box: {e}")
                shape_ids.append(self._create_box_shape(1.0, 1.0, 1.0))
        elif col_type == 'mesh' and getattr(obj, 'model_path', '') and os.path.exists(obj.model_path):
            ext = os.path.splitext(obj.model_path)[1].lower()
            if ext in ('.glb', '.gltf'):
                shape_ids = self._create_mesh_collision(obj, sx, sy, sz)
            elif ext == '.obj':
                shape_ids.append(p.createCollisionShape(
                    p.GEOM_MESH, fileName=obj.model_path, meshScale=[sx, sy, sz],
                    physicsClientId=self.client_id))
            else:
                shape_ids = self._create_mesh_collision(obj, sx, sy, sz)
        elif col_type == 'convex_hull':
            shape_ids = self._create_mesh_collision(obj, sx, sy, sz, force_convex=True)
        else:
            try:
                shape_ids.append(self._create_box_shape(sx, sy, sz))
            except Exception as e:
                print(f"[Physics] WARNING: Default collider failed for {obj.name}, falling back to unit box: {e}")
                shape_ids.append(self._create_box_shape(1.0, 1.0, 1.0))

        body_pos = glm.vec3(obj.position) + self._offset_world(obj)
        pos = [body_pos.x, body_pos.y, body_pos.z]
        quat = [obj.rotation.x, obj.rotation.y, obj.rotation.z, obj.rotation.w]

        # Register one or more bodies (chunks) for this object
        body_ids = []
        for sid in shape_ids:
            bid = p.createMultiBody(
                baseMass=mass,
                baseCollisionShapeIndex=sid,
                basePosition=pos,
                baseOrientation=quat,
                physicsClientId=self.client_id,
            )
            body_ids.append(bid)
            self._body_to_obj[bid] = obj
        # Performance Optimization: Only apply the 'smooth' margin to primitives.
        # High-poly meshes (like WorldB) must use a 0.0 margin to avoid a massive FPS hit.
        margin = 0.0 if col_type in ('mesh', 'convex_hull') else 0.04

        angular_damp = 0.99 if col_type in ('capsule', 'sphere') else 0.05
        for bid in body_ids:
            p.changeDynamics(bid, -1,
                             restitution=bounciness,
                             lateralFriction=friction,
                             linearDamping=drag,
                             angularDamping=angular_damp,
                             collisionMargin=margin,
                             physicsClientId=self.client_id)
            
            if getattr(obj, 'is_trigger', False):
                p.setCollisionFilterGroupMask(bid, -1, 0, 0, physicsClientId=self.client_id)

        # pybullet_body_id remains an int (the primary part) for script compatibility.
        # pybullet_body_ids stores the full list for internal physics management.
        obj.pybullet_body_id = body_ids[0]
        obj.pybullet_body_ids = body_ids
        
        self.body_map[obj] = obj.pybullet_body_id
        self.body_scales[obj] = glm.vec3(sx, sy, sz)
        self._cached_dynamics[obj] = self._dynamics_key(obj)

    def _create_mesh_collision(self, obj, sx, sy, sz, force_convex=False):
        """Create triangle mesh or convex hull collision shapes. 
        Splits high-poly meshes into multiple chunks to stay under PyBullet vertex limits.
        """
        shape_ids = []
        
        def commit_chunk(positions, indices):
            """Internal helper to build one collision chunk and return its shape ID."""
            # Deduplicate vertices for convex hulls
            if force_convex:
                final_verts = np.unique(positions, axis=0)
            else:
                final_verts = positions

            try:
                if not force_convex and indices:
                    return p.createCollisionShape(
                        p.GEOM_MESH,
                        vertices=final_verts.tolist(),
                        indices=np.concatenate(indices).tolist() if isinstance(indices, list) else indices.tolist(),
                        meshScale=[1, 1, 1],
                        physicsClientId=self.client_id)
                else:
                    return p.createCollisionShape(
                        p.GEOM_MESH,
                        vertices=final_verts.tolist(),
                        meshScale=[1, 1, 1],
                        physicsClientId=self.client_id)
            except Exception as e:
                print(f"[Physics] ERROR: Chunk creation failed for {obj.name}: {e}")
                return None

        current_chunk_verts = []
        current_chunk_indices = []
        current_vcount = 0
        v_offset = 0

        for mesh in obj.meshes:
            positions = mesh._mesh_data.get('collision_verts')
            if positions is None:
                raw = mesh._mesh_data.get('vertices')
                if raw is None or len(raw) == 0: continue
                floats_per_vert = 16 if mesh._has_skin else 8
                positions = raw.reshape(-1, floats_per_vert)[:, :3].astype('f4')
            
            if positions is None or len(positions) == 0: continue
            
            scaled_pos = positions * np.array([sx, sy, sz], dtype='f4')
            mesh_indices = mesh._mesh_data.get('indices')
            if mesh_indices is None:
                n = len(positions)
                mesh_indices = np.arange(n, dtype=np.uint32)

            # --- Chunking Logic ---
            # If adding this mesh would exceed the 60k limit, finalize the current chunk first.
            if current_vcount + len(scaled_pos) > 60000 and current_chunk_verts:
                sid = commit_chunk(np.concatenate(current_chunk_verts), current_chunk_indices)
                if sid is not None: shape_ids.append(sid)
                current_chunk_verts = []
                current_chunk_indices = []
                current_vcount = 0
                v_offset = 0

            current_chunk_verts.append(scaled_pos)
            current_chunk_indices.append(mesh_indices.astype(np.uint32) + v_offset)
            current_vcount += len(scaled_pos)
            v_offset += len(scaled_pos)

        # Finalize the last chunk
        if current_chunk_verts:
            sid = commit_chunk(np.concatenate(current_chunk_verts), current_chunk_indices)
            if sid is not None: shape_ids.append(sid)

        if not shape_ids:
            print(f"[Physics] Warning: No mesh chunks found for {obj.name}, using box fallback")
            shape_ids.append(p.createCollisionShape(
                p.GEOM_BOX, halfExtents=[sx * 0.5, sy * 0.5, sz * 0.5],
                physicsClientId=self.client_id))
            
        return shape_ids

    def remove_object(self, obj):
        """Remove all physical parts of an object from PyBullet world."""
        body_ids = getattr(obj, 'pybullet_body_ids', None)
        if body_ids is None:
            # Fallback for objects that might only have the single ID
            body_ids = getattr(obj, 'pybullet_body_id', None)
            if body_ids is None: return
            if not isinstance(body_ids, list): body_ids = [body_ids]

        for bid in body_ids:
            self._body_to_obj.pop(bid, None)
            p.removeBody(bid, physicsClientId=self.client_id)
            
        self.body_map.pop(obj, None)
        self.body_scales.pop(obj, None)
        self._cached_dynamics.pop(obj, None)
        obj.pybullet_body_id = None
        obj.pybullet_body_ids = None

    def reset(self):
        """Tear down all bodies and start fresh."""
        for obj in list(self.body_map):
            self.remove_object(obj)
        self._time_accumulator = 0.0

    def step(self, dt, scene_objects):
        """Step the simulation with proper fixed-timestep accumulation
        and sync transforms back to SceneObjects.
        Returns the number of physics substeps taken this frame."""

        # --- Pre-step: register new objects, handle dirty state, update dynamics ---
        for obj in scene_objects:
            body_id = getattr(obj, 'pybullet_body_id', None)
            is_collideable = getattr(obj, 'is_collideable', True)

            if not is_collideable:
                if body_id is not None:
                    self.remove_object(obj)
                    obj._physics_dirty = False
                continue

            if body_id is None:
                self.add_object(obj)
                continue

            sx, sy, sz = self._extract_scale(obj)
            cur_scale = glm.vec3(sx, sy, sz)
            last_scale = self.body_scales.get(obj)
            if last_scale and glm.distance(cur_scale, last_scale) > 1e-4:
                self.remove_object(obj)
                self.add_object(obj)
                continue

            is_kinematic = getattr(obj, 'is_kinematic', True)
            if is_kinematic or getattr(obj, 'mass', 1.0) == 0.0 or getattr(obj, '_physics_dirty', False):
                body_pos = glm.vec3(obj.position) + self._offset_world(obj)
                pos = [body_pos.x, body_pos.y, body_pos.z]
                quat = [obj.rotation.x, obj.rotation.y, obj.rotation.z, obj.rotation.w]
                
                # Update all chunks of the body
                body_ids = getattr(obj, 'pybullet_body_ids', [body_id])
                for bid in body_ids:
                    p.resetBasePositionAndOrientation(bid, pos, quat,
                                                      physicsClientId=self.client_id)
                    if getattr(obj, '_physics_dirty', False):
                        p.resetBaseVelocity(bid, [0, 0, 0], [0, 0, 0],
                                            physicsClientId=self.client_id)
                
                if getattr(obj, '_physics_dirty', False):
                    obj._physics_dirty = False
                self.body_scales[obj] = cur_scale

            new_dyn = self._dynamics_key(obj)
            if self._cached_dynamics.get(obj) != new_dyn:
                mass = 0.0 if is_kinematic else getattr(obj, 'mass', 1.0)
                # Update dynamics for all chunks
                # Dynamic Margin Update
                col_type = getattr(obj, 'collider_type', 'box')
                margin = 0.0 if col_type in ('mesh', 'convex_hull') else 0.04

                for bid in body_ids:
                    p.changeDynamics(bid, -1,
                                     mass=mass,
                                     restitution=getattr(obj, 'bounciness', 0.0),
                                     lateralFriction=getattr(obj, 'friction', 0.5),
                                     linearDamping=getattr(obj, 'drag', 0.02),
                                     angularDamping=0.05,
                                     collisionMargin=margin,
                                     physicsClientId=self.client_id)
                self._cached_dynamics[obj] = new_dyn

        # --- Fixed-timestep accumulation ---
        self._time_accumulator += dt
        num_steps = min(int(self._time_accumulator / FIXED_TIMESTEP), MAX_SUBSTEPS)
        self._time_accumulator -= num_steps * FIXED_TIMESTEP

        # Apply per-body forces before stepping (merged into one pass to reduce iterations)
        if num_steps > 0:
            grav = self.gravity
            cid = self.client_id
            for obj in scene_objects:
                body_id = getattr(obj, 'pybullet_body_id', None)
                if body_id is None:
                    continue
                if getattr(obj, 'is_kinematic', True):
                    continue
                use_grav = getattr(obj, 'use_gravity', False)
                mass = getattr(obj, 'mass', 1.0)
                if not use_grav and mass > 0:
                    body_ids = getattr(obj, 'pybullet_body_ids', [body_id])
                    anti_grav = [0, -grav * mass, 0]
                    for bid in body_ids:
                        p.applyExternalForce(bid, -1, anti_grav, [0, 0, 0], p.WORLD_FRAME,
                                             physicsClientId=cid)

        for _ in range(num_steps):
            p.stepSimulation(physicsClientId=self.client_id)

        # --- Collision detection ---
        self.collisions.clear()
        if num_steps > 0:
            contacts = p.getContactPoints(physicsClientId=self.client_id)
            for cp in contacts:
                body_a, body_b = cp[1], cp[2]
                obj_a = self._body_to_obj.get(body_a)
                obj_b = self._body_to_obj.get(body_b)
                if obj_a is None or obj_b is None:
                    continue
                pt = glm.vec3(cp[5][0], cp[5][1], cp[5][2])
                normal = glm.vec3(cp[7][0], cp[7][1], cp[7][2])
                impulse = cp[9]
                self.collisions.append((obj_a, obj_b, pt, normal, impulse))

        # --- Post-step: air resistance + sync back to scene ---
        for obj in scene_objects:
            body_id = getattr(obj, 'pybullet_body_id', None)
            if body_id is None:
                continue

            is_kinematic = getattr(obj, 'is_kinematic', True)
            if is_kinematic or getattr(obj, 'mass', 1.0) == 0.0:
                continue

            mass = obj.mass
            drag = getattr(obj, 'drag', 0.02)
            if drag > 0 and mass > 0:
                damping_factor = min((drag * AIR_RESISTANCE_STRENGTH) / mass, 0.95)
                vel, ang_vel = p.getBaseVelocity(body_id, physicsClientId=self.client_id)
                retain = 1.0 - damping_factor
                p.resetBaseVelocity(body_id,
                                    [vel[0] * retain, vel[1] * retain, vel[2] * retain],
                                    list(ang_vel),
                                    physicsClientId=self.client_id)

            pos, quat = p.getBasePositionAndOrientation(body_id,
                                                        physicsClientId=self.client_id)
            obj.update_transform(pos, quat, collider_offset=self._extract_offset(obj))

        return num_steps

    def raycast(self, ray_from, ray_to, ignore=None):
        """Raycast using PyBullet's physics engine.

        Args:
            ray_from: glm.vec3 or list [x,y,z] - start point
            ray_to: glm.vec3 or list [x,y,z] - end point

        Returns:
            The SceneObject hit, or None if no hit.
        """
        hit = self.raycast_detailed(ray_from, ray_to, ignore=ignore)
        return hit[0] if hit else None

    def raycast_detailed(self, ray_from, ray_to, ignore=None):
        """Detailed raycast using PyBullet's physics engine.

        Args:
            ray_from: glm.vec3 or list [x,y,z] - start point
            ray_to: glm.vec3 or list [x,y,z] - end point

        Returns:
            Tuple (hit_object, hit_position, hit_fraction, hit_normal) or None if no hit.
            - hit_object: The SceneObject hit, or None
            - hit_position: glm.vec3 world position of hit point
            - hit_fraction: 0.0-1.0 along the ray where hit occurred
            - hit_normal: glm.vec3 surface normal at hit point
        """
        if isinstance(ray_from, glm.vec3):
            ray_from = [ray_from.x, ray_from.y, ray_from.z]
        if isinstance(ray_to, glm.vec3):
            ray_to = [ray_to.x, ray_to.y, ray_to.z]

        results = p.rayTest(ray_from, ray_to, physicsClientId=self.client_id)
        if not results:
            return None

        closest_hit = results[0]
        body_id = closest_hit[0]

        if body_id == -1:
            return None

        hit_obj = self._body_to_obj.get(body_id)
        if hit_obj is None:
            return None

        hit_fraction = closest_hit[2]
        hit_position_world = closest_hit[3]
        
        ray_dir = glm.vec3(
            ray_to[0] - ray_from[0],
            ray_to[1] - ray_from[1],
            ray_to[2] - ray_from[2],
        )
        ray_length = glm.length(ray_dir)
        if ray_length > 0.001:
            ray_dir = glm.normalize(ray_dir)
        
        hit_pos = glm.vec3(
            ray_from[0] + ray_dir.x * ray_length * hit_fraction,
            ray_from[1] + ray_dir.y * ray_length * hit_fraction,
            ray_from[2] + ray_dir.z * ray_length * hit_fraction,
        )
        
        hit_normal = glm.vec3(0.0, 1.0, 0.0)
        
        return (hit_obj, hit_pos, hit_fraction, hit_normal)
