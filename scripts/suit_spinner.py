import math
import glm

SPIN_SPEED = 60.0
BOP_SPEED = 3.0
BOP_AMOUNT = 0.15


class SuitSpinner:
    def start(self):
        self._initial_y = self.entity.position.y
        self._time = 0.0
        self._rot_y = 0.0

    def update(self, dt):
        self._time += dt
        
        self._rot_y += SPIN_SPEED * dt
        self.entity.set_rotation_euler(0, self._rot_y, 0)
        
        bop_offset = math.sin(self._time * BOP_SPEED) * BOP_AMOUNT
        self.entity.position = glm.vec3(self.entity.position.x, self._initial_y + bop_offset, self.entity.position.z)

    def on_interact(self):
        print(f"[SuitSpinner] {self.entity.name} collected!")
        self.engine.audio.play_sfx('assets/sounds/bloodGushing.mp3')
        self.engine.destroy(self.entity)
