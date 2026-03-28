import pybullet as p

SEQUENCE_LIGHTS = ['light_2', 'light_3', 'light_4', 'light_5', 'light_6', 'light_7', 'light_8', 'light_9']
SEQUENCE_DELAY  = 3.0   # seconds after trigger before sequence starts
SEQUENCE_STEP   = 0.2   # seconds between each light in the sequence


class BosshallwayLight:
    """On first player entry: turn on light_1 immediately, then after 3s
    turn on light_2 through light_9 one by one every 0.2 seconds."""

    def start(self):
        self.triggered   = False
        self.timer       = 0.0
        self.state       = 'WAITING'   # WAITING → DELAY → SEQUENCE → DONE
        self.seq_index   = 0

        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            phys = self.engine.physics_system
            p.setCollisionFilterGroupMask(body_id, -1, 0, 0, physicsClientId=phys.client_id)

    def _set_light(self, name):
        light = next((o for o in self.engine.scene_objects if o.name == name), None)
        if light is not None:
            light.light_intensity = 0.06
            light.alpha = 1.0
        else:
            print(f'[BosshallwayLight] WARNING: {name} not found')

    def update(self, dt):
        if self.state == 'DONE':
            return

        if self.state == 'WAITING':
            player = self.engine.interaction_manager._get_player()
            if not player or not hasattr(player, 'pybullet_body_id'):
                return
            trigger_id = getattr(self.entity, 'pybullet_body_id', None)
            if trigger_id is None:
                return
            points = p.getClosestPoints(player.pybullet_body_id, trigger_id,
                                        distance=0.0, physicsClientId=self.engine.physics_system.client_id)
            if not points:
                return

            # Player entered — fire light_1 immediately and start delay
            self._set_light('light_1')
            self.timer = 0.0
            self.state = 'DELAY'

        elif self.state == 'DELAY':
            self.timer += dt
            if self.timer >= SEQUENCE_DELAY:
                self.timer = 0.0
                self.seq_index = 0
                self.state = 'SEQUENCE'

        elif self.state == 'SEQUENCE':
            self.timer += dt
            # Turn on every light whose turn has come
            while self.seq_index < len(SEQUENCE_LIGHTS) and \
                  self.timer >= self.seq_index * SEQUENCE_STEP:
                self._set_light(SEQUENCE_LIGHTS[self.seq_index])
                self.seq_index += 1

            if self.seq_index >= len(SEQUENCE_LIGHTS):
                self.state = 'DONE'
