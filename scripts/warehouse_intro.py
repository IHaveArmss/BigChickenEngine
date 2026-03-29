import glm
import pygame


PRESS_TARGET = 5
INITIAL_BEHIND_DISTANCE = 0.2
FINAL_FRONT_DISTANCE = 1.5


class WarehouseIntro:
    """Warehouse scene intro: freeze the player behind Legat until E is pressed five times."""

    def start(self):
        self._press_count = 0
        self._done = False
        self._legat = self._find_legat()
        self._locked_position = None
        self._final_position = None
        self._original_is_collideable = getattr(self.entity, 'is_collideable', True)

        if self._legat is None:
            print("[WarehouseIntro] WARNING: legat object not found")
            return

        self._locked_position = self._behind_legat(INITIAL_BEHIND_DISTANCE)
        self._final_position = self._in_front_of_legat(FINAL_FRONT_DISTANCE)

        self.entity.position = self._locked_position
        self.entity.alpha = 0.0
        self.entity.is_collideable = False
        self.entity._physics_dirty = True

        if hasattr(self.engine, 'hud'):
            self.engine.hud.show_prompt("Press E repeatedly", f"0 / {PRESS_TARGET}")

        if hasattr(self.engine, 'lock_player_input'):
            self.engine.lock_player_input()

    def update(self, dt):
        if self._done or self._locked_position is None:
            return

        self.entity.position = glm.vec3(self._locked_position)
        self.entity.alpha = 0.0

    def on_key_down(self, key, mod=0):
        if self._done or key != pygame.K_e or self._locked_position is None:
            return False

        self._press_count += 1
        if self._press_count >= PRESS_TARGET:
            self._complete()
            return True

        if hasattr(self.engine, 'hud'):
            self.engine.hud.show_prompt("Press E repeatedly", f"{self._press_count} / {PRESS_TARGET}")
        return True

    def _complete(self):
        self._done = True
        if self._final_position is not None:
            self.entity.position = glm.vec3(self._final_position)
        self.entity.alpha = 1.0
        self.entity.is_collideable = self._original_is_collideable
        self.entity._physics_dirty = True

        if self._legat is not None:
            self._legat.alpha = 0.0

        if hasattr(self.engine, 'hud'):
            self.engine.hud.hide_prompt()
        if hasattr(self.engine, 'unlock_player_input'):
            self.engine.unlock_player_input()

    def _find_legat(self):
        for obj in self.engine.scene_objects:
            if obj.name == 'legat':
                return obj
        return None

    def _behind_legat(self, distance):
        legat_pos = glm.vec3(self._legat.position)
        player_pos = glm.vec3(self.entity.position)
        legat_yaw = float(getattr(self._legat.rotation_euler, 'y', 0.0))
        yaw_rad = glm.radians(legat_yaw)
        forward = glm.vec3(-glm.sin(yaw_rad), 0.0, -glm.cos(yaw_rad))

        return glm.vec3(
            legat_pos.x - forward.x * distance,
            player_pos.y,
            legat_pos.z - forward.z * distance,
        )

    def _in_front_of_legat(self, distance):
        legat_pos = glm.vec3(self._legat.position)
        player_pos = glm.vec3(self.entity.position)
        legat_yaw = float(getattr(self._legat.rotation_euler, 'y', 0.0))
        yaw_rad = glm.radians(legat_yaw)
        forward = glm.vec3(-glm.sin(yaw_rad), 0.0, -glm.cos(yaw_rad))

        return glm.vec3(
            legat_pos.x - forward.x * distance,
            player_pos.y,
            legat_pos.z - forward.z * distance,
        )
