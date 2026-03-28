import pybullet as p
import glm

CLOSE_SPEED = 4.0  # units per second


class ElevatorCloseTrigger:
    """On first player entry, smoothly returns the elevator doors to their
    original positions (recorded at scene start)."""

    def start(self):
        self._triggered = False
        self._moving    = False
        self._left      = None
        self._right     = None
        self._origin_l  = None
        self._origin_r  = None
        self._start_l   = None
        self._start_r   = None
        self._t         = 0.0

        # Ghost — player walks through
        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            p.setCollisionFilterGroupMask(body_id, -1, 0, 0,
                                          physicsClientId=self.engine.physics_system.client_id)

        # Record door positions before any movement happens
        for obj in self.engine.scene_objects:
            if obj.name == 'elevator_left_door':
                self._left     = obj
                self._origin_l = glm.vec3(obj.position)
            elif obj.name == 'elevator_right_door':
                self._right    = obj
                self._origin_r = glm.vec3(obj.position)

    def update(self, dt):
        if self._triggered and not self._moving:
            return

        if not self._triggered:
            player = self.engine.interaction_manager._get_player()
            if not player or not hasattr(player, 'pybullet_body_id'):
                return
            trigger_id = getattr(self.entity, 'pybullet_body_id', None)
            if trigger_id is None:
                return
            points = p.getClosestPoints(player.pybullet_body_id, trigger_id,
                                        distance=0.0,
                                        physicsClientId=self.engine.physics_system.client_id)
            if not points:
                return

            self._triggered = True
            if self._left is None or self._right is None:
                return
            self._start_l = glm.vec3(self._left.position)
            self._start_r = glm.vec3(self._right.position)
            self._t       = 0.0
            self._moving  = True

        if self._moving:
            dist = max(
                glm.length(self._start_l - self._origin_l),
                glm.length(self._start_r - self._origin_r),
                0.001,
            )
            self._t = min(1.0, self._t + dt / (dist / CLOSE_SPEED))
            t = self._t * self._t * (3.0 - 2.0 * self._t)

            self._left.position  = glm.mix(self._start_l, self._origin_l, t)
            self._right.position = glm.mix(self._start_r, self._origin_r, t)

            if self._t >= 1.0:
                self._moving = False
