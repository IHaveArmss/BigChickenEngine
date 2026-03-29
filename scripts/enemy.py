import pybullet as p
import glm
import math
import random

MOVE_SPEED_BASE = 3.0   # reference speed for animation scaling
MOVE_SPEED_MIN = 3.0    # 50% variance in speeds — makes the horde less uniform
MOVE_SPEED_MAX = 5.0
ATTACK_RANGE = 1.5      # stop moving when this close


class Enemy:
    """Pathfinds toward the player every frame.
    Killed by the weapon via die() — called from weapon.py when shot."""

    def start(self):
        self.move_speed = random.uniform(MOVE_SPEED_MIN, MOVE_SPEED_MAX)
        
        # Scale animation speed to match movement speed if animator exists
        if getattr(self.entity, 'animator', None) is not None:
            self.entity.animator.speed = self.move_speed / MOVE_SPEED_BASE

        self.entity.is_enemy = True
        self._dead = False
        self._enabled = False
        self._original_alpha = 1.0  # Default to full opacity
        self.entity.alpha = 0.0
        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            phys = self.engine.physics_system
            p.setCollisionFilterGroupMask(body_id, -1, 0, 0, physicsClientId=phys.client_id)
            p.changeDynamics(body_id, -1, mass=0, physicsClientId=phys.client_id)

    def set_enabled(self, enabled):
        self._enabled = enabled
        if enabled:
            self.entity.alpha = 1.0
            body_id = getattr(self.entity, 'pybullet_body_id', None)
            if body_id is not None:
                phys = self.engine.physics_system
                p.setCollisionFilterGroupMask(body_id, -1, 1, 1, physicsClientId=phys.client_id)
                p.changeDynamics(body_id, -1, mass=50.0, physicsClientId=phys.client_id)
        else:
            self.entity.alpha = 0.0
            body_id = getattr(self.entity, 'pybullet_body_id', None)
            if body_id is not None:
                phys = self.engine.physics_system
                p.setCollisionFilterGroupMask(body_id, -1, 0, 0, physicsClientId=phys.client_id)
                p.changeDynamics(body_id, -1, mass=0, physicsClientId=phys.client_id)

    def update(self, dt):
        if self._dead or not self._enabled:
            return

        player = self.engine.interaction_manager._get_player()
        if player is None:
            return

        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is None:
            return

        phys_id = self.engine.physics_system.client_id
        to_player = player.position - self.entity.position
        flat      = glm.vec3(to_player.x, 0.0, to_player.z)
        dist      = glm.length(flat)

        # Current vertical velocity (preserve gravity)
        cur_vel, _ = p.getBaseVelocity(body_id, physicsClientId=phys_id)

        if dist > ATTACK_RANGE:
            direction = glm.normalize(flat)
            p.resetBaseVelocity(
                body_id,
                [direction.x * self.move_speed, cur_vel[1], direction.z * self.move_speed],
                [0, 0, 0],
                physicsClientId=phys_id,
            )
            # Face player — use positive flat components so the mesh front points toward the player
            angle = math.atan2(flat.x, flat.z)
            self.entity.set_rotation_euler(0, math.degrees(angle), 0)
        else:
            # Stop horizontal movement when close
            p.resetBaseVelocity(
                body_id,
                [0.0, cur_vel[1], 0.0],
                [0, 0, 0],
                physicsClientId=phys_id,
            )

    def die(self):
        if self._dead:
            return
        self._dead = True
        self.engine.audio.play_sfx('assets/sounds/bloodGushing.mp3')
        self.engine.destroy(self.entity)
