import glm

SLIDE_SPEED = 4.0   # units per second for both phases
X_DISTANCE  = 0.5   # phase 1: pull doors out on X
Z_DISTANCE  = 10.0  # phase 2: slide doors apart on Z


class ElevatorButton:
    """Two-phase elevator door opener:
      Phase 1 — both doors slide +1 X
      Phase 2 — left door +10 Z, right door -10 Z"""

    def start(self):
        self._phase  = 0   # 0=idle, 1=X move, 2=Z move, 3=done
        self._left   = None
        self._right  = None
        self._start_l = None
        self._start_r = None
        self._target_l = None
        self._target_r = None
        self._t = 0.0

    def _find_doors(self):
        for obj in self.engine.scene_objects:
            if obj.name == 'elevator_left_door':
                self._left = obj
            elif obj.name == 'elevator_right_door':
                self._right = obj

    def _begin_phase(self, phase):
        self._phase = phase
        self._t = 0.0
        self._start_l = glm.vec3(self._left.position)
        self._start_r = glm.vec3(self._right.position)
        if phase == 1:
            self._target_l = self._start_l + glm.vec3(X_DISTANCE, 0, 0)
            self._target_r = self._start_r + glm.vec3(X_DISTANCE, 0, 0)
        elif phase == 2:
            self._target_l = self._start_l + glm.vec3(0, 0,  Z_DISTANCE)
            self._target_r = self._start_r + glm.vec3(0, 0, -Z_DISTANCE)

    def on_interact(self):
        if self._phase != 0:
            return
        self._find_doors()
        if self._left is None or self._right is None:
            print("[ElevatorButton] Could not find elevator door objects")
            return
        self._begin_phase(1)

    def update(self, dt):
        if self._phase not in (1, 2):
            return

        distance = X_DISTANCE if self._phase == 1 else Z_DISTANCE
        self._t = min(1.0, self._t + dt / (distance / SLIDE_SPEED))
        t = self._t * self._t * (3.0 - 2.0 * self._t)  # smoothstep

        self._left.position  = glm.mix(self._start_l, self._target_l, t)
        self._right.position = glm.mix(self._start_r, self._target_r, t)

        if self._t >= 1.0:
            if self._phase == 1:
                self._begin_phase(2)
            else:
                self._phase = 3
