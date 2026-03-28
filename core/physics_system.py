import pybullet as p
import pybullet_data
import glm
import os
import struct

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
        s = obj.scale
        return (s.x if hasattr(s, 'x') else s[0],
                s.y if hasattr(s, 'y') else s[1],
                s.z if hasattr(s, 'z') else s[2])

    def _dynamics_key(self, obj):
        """Return a hashable snapshot of the physics-relevant properties."""
        is_kin = getattr(obj, 'is_kinematic', True)
        mass = 0.0 if is_kin else getattr(obj, 'mass', 1.0)
        return (mass,
                getattr(obj, 'bounciness', 0.0),
                getattr(obj, 'friction', 0.5),
                getattr(obj, 'drag', 0.02),
                getattr(obj, 'use_gravity', False))

    def add_object(self, obj):
        """Register a SceneObject into the PyBullet world."""
        if not getattr(obj, 'is_collideable', True):
            return
            
        is_kinematic = getattr(obj, 'is_kinematic', True)
        mass = 0.0 if is_kinematic else getattr(obj, 'mass', 1.0)
        bounciness = getattr(obj, 'bounciness', 0.0)
        friction = getattr(obj, 'friction', 0.5)
        drag = getattr(obj, 'drag', 0.02)
        use_gravity = getattr(obj, 'use_gravity', False)

        col_type = getattr(obj, 'collider_type', 'box')
        sx, sy, sz = self._extract_scale(obj)

        if col_type == 'box':
            shape_id = p.createCollisionShape(
                p.GEOM_BOX, halfExtents=[sx * 0.5, sy * 0.5, sz * 0.5],
                physicsClientId=self.client_id)
        elif col_type == 'sphere':
            shape_id = p.createCollisionShape(
                p.GEOM_SPHERE, radius=max(sx, sy, sz) * 0.5,
                physicsClientId=self.client_id)
        elif col_type == 'mesh' and getattr(obj, 'model_path', '') and os.path.exists(obj.model_path):
            ext = os.path.splitext(obj.model_path)[1].lower()
            if ext in ('.glb', '.gltf'):
                # PyBullet doesn't support .glb files for GEOM_MESH via fileName.
                # Use our memory-based triangle mesh/convex hull generator instead.
                shape_id = self._create_mesh_collision(obj, sx, sy, sz)
            elif ext == '.obj':
                shape_id = p.createCollisionShape(
                    p.GEOM_MESH, fileName=obj.model_path, meshScale=[sx, sy, sz],
                    physicsClientId=self.client_id)
            else:
                # Fallback for other formats (stl, etc.)
                shape_id = self._create_mesh_collision(obj, sx, sy, sz)
        elif col_type == 'convex_hull':
            shape_id = self._create_mesh_collision(obj, sx, sy, sz)
        else:
            shape_id = p.createCollisionShape(
                p.GEOM_BOX, halfExtents=[sx * 0.5, sy * 0.5, sz * 0.5],
                physicsClientId=self.client_id)

        pos = [obj.position.x, obj.position.y, obj.position.z]
        quat = [obj.rotation.x, obj.rotation.y, obj.rotation.z, obj.rotation.w]

        body_id = p.createMultiBody(
            baseMass=mass,
            baseCollisionShapeIndex=shape_id,
            basePosition=pos,
            baseOrientation=quat,
            physicsClientId=self.client_id,
        )

        p.changeDynamics(body_id, -1,
                         restitution=bounciness,
                         lateralFriction=friction,
                         linearDamping=drag,
                         angularDamping=0.05,
                         physicsClientId=self.client_id)
        
        # --- Trigger Support (Ghost Mode) ---
        if getattr(obj, 'is_trigger', False):
            p.setCollisionFilterGroupMask(body_id, -1, 0, 0, physicsClientId=self.client_id)

        obj.pybullet_body_id = body_id
        self.body_map[obj] = body_id
        self._body_to_obj[body_id] = obj
        self.body_scales[obj] = glm.vec3(sx, sy, sz)
        self._cached_dynamics[obj] = self._dynamics_key(obj)

    def _create_mesh_collision(self, obj, sx, sy, sz):
        """Create a triangle mesh (concave, for static) or convex hull collision shape."""
        vertices = []
        indices = []
        vertex_offset = 0
        
        for mesh in obj.meshes:
            vbo = mesh.vbo
            if vbo is None:
                continue
            
            try:
                data = vbo.read()
                fmt = mesh.get_vertex_data_format()
                floats_per_vert = sum(int(f[0].replace('f', '')) for f in fmt)
                pos_stride = floats_per_vert * 4
                
                num_verts = len(data) // pos_stride
                for i in range(num_verts):
                    offset = i * pos_stride
                    x = struct.unpack_from('f', data, offset)[0]
                    y = struct.unpack_from('f', data, offset + 4)[0]
                    z = struct.unpack_from('f', data, offset + 8)[0]
                    vertices.append([x * sx, y * sy, z * sz])
                
                # Extract indices if available
                mesh_indices = mesh._mesh_data.get('indices')
                if mesh_indices is not None:
                    # Offset indices by the current number of global vertices
                    indices.extend((mesh_indices + vertex_offset).tolist())
                else:
                    # If no indices, we can't easily make a triangle mesh for this sub-mesh
                    # but we can at least add fake indices if we want true mesh collision
                    for i in range(0, num_verts, 3):
                        if i + 2 < num_verts:
                            indices.extend([vertex_offset + i, vertex_offset + i + 1, vertex_offset + i + 2])
                
                vertex_offset += num_verts
            except Exception as e:
                print(f"[Physics] Warning: Could not extract mesh data: {e}")
                continue
        
        if not vertices:
            print(f"[Physics] Warning: No vertices found for {obj.name}, using box fallback")
            return p.createCollisionShape(
                p.GEOM_BOX, halfExtents=[sx * 0.5, sy * 0.5, sz * 0.5],
                physicsClientId=self.client_id)
        
        mass = getattr(obj, 'mass', 1.0)
        # Use GEOM_MESH with indices for concave collision if static (mass=0)
        # Dynamic objects in PyBullet MUST be convex hulls for stable collision.
        if mass == 0.0 and indices:
            return p.createCollisionShape(
                p.GEOM_MESH, vertices=vertices, indices=indices,
                physicsClientId=self.client_id)
        else:
            return p.createCollisionShape(
                p.GEOM_MESH, vertices=vertices,
                physicsClientId=self.client_id)

    def remove_object(self, obj):
        """Remove an object from PyBullet world."""
        if getattr(obj, 'pybullet_body_id', None) is not None:
            self._body_to_obj.pop(obj.pybullet_body_id, None)
            p.removeBody(obj.pybullet_body_id, physicsClientId=self.client_id)
            self.body_map.pop(obj, None)
            self.body_scales.pop(obj, None)
            self._cached_dynamics.pop(obj, None)
            obj.pybullet_body_id = None

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
                pos = [obj.position.x, obj.position.y, obj.position.z]
                quat = [obj.rotation.x, obj.rotation.y, obj.rotation.z, obj.rotation.w]
                p.resetBasePositionAndOrientation(body_id, pos, quat,
                                                  physicsClientId=self.client_id)
                if getattr(obj, '_physics_dirty', False):
                    p.resetBaseVelocity(body_id, [0, 0, 0], [0, 0, 0],
                                        physicsClientId=self.client_id)
                    obj._physics_dirty = False
                self.body_scales[obj] = cur_scale

            new_dyn = self._dynamics_key(obj)
            if self._cached_dynamics.get(obj) != new_dyn:
                mass = 0.0 if is_kinematic else getattr(obj, 'mass', 1.0)
                p.changeDynamics(body_id, -1,
                                 mass=mass,
                                 restitution=getattr(obj, 'bounciness', 0.0),
                                 lateralFriction=getattr(obj, 'friction', 0.5),
                                 linearDamping=getattr(obj, 'drag', 0.02),
                                 angularDamping=0.05,
                                 physicsClientId=self.client_id)
                self._cached_dynamics[obj] = new_dyn

        # --- Fixed-timestep accumulation ---
        self._time_accumulator += dt
        num_steps = min(int(self._time_accumulator / FIXED_TIMESTEP), MAX_SUBSTEPS)
        self._time_accumulator -= num_steps * FIXED_TIMESTEP

        # Apply per-body gravity override before stepping
        for obj in scene_objects:
            body_id = getattr(obj, 'pybullet_body_id', None)
            if body_id is None:
                continue
            if getattr(obj, 'is_kinematic', True):
                continue
            if not getattr(obj, 'use_gravity', False):
                mass = getattr(obj, 'mass', 1.0)
                if mass > 0:
                    p.applyExternalForce(body_id, -1,
                                         [0, -self.gravity * mass, 0],
                                         [0, 0, 0], p.WORLD_FRAME,
                                         physicsClientId=self.client_id)

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
            obj.update_transform(pos, quat)

        return num_steps

    def raycast(self, ray_from, ray_to):
        """Raycast using PyBullet's physics engine.

        Args:
            ray_from: glm.vec3 or list [x,y,z] - start point
            ray_to: glm.vec3 or list [x,y,z] - end point

        Returns:
            The SceneObject hit, or None if no hit.
        """
        hit = self.raycast_detailed(ray_from, ray_to)
        return hit[0] if hit else None

    def raycast_detailed(self, ray_from, ray_to):
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
