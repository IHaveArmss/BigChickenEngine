import pybullet as p
import pybullet_data
import glm
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
                getattr(obj, 'use_gravity', False),
                getattr(obj, 'is_collideable', True))

    def add_object(self, obj):
        """Register a SceneObject into the PyBullet world."""
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
            shape_id = p.createCollisionShape(
                p.GEOM_MESH, fileName=obj.model_path, meshScale=[sx, sy, sz],
                physicsClientId=self.client_id)
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

        if not getattr(obj, 'is_collideable', True):
            p.setCollisionFilterGroupMask(body_id, -1, 0, 0, physicsClientId=self.client_id)

        obj.pybullet_body_id = body_id
        self.body_map[obj] = body_id
        self._body_to_obj[body_id] = obj
        self.body_scales[obj] = glm.vec3(sx, sy, sz)
        self._cached_dynamics[obj] = self._dynamics_key(obj)

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
                if getattr(obj, 'is_collideable', True):
                    p.setCollisionFilterGroupMask(body_id, -1, 1, -1, physicsClientId=self.client_id)
                else:
                    p.setCollisionFilterGroupMask(body_id, -1, 0, 0, physicsClientId=self.client_id)
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

        return self._body_to_obj.get(body_id)
