import pybullet as p
import random

# Toggles and Settings
USE_FLICKER     = True  # SET TO False TO REMOVE THE DRAMATIC FLICKER
SEQUENCE_LIGHTS = ['light_1', 'light_2', 'light_3', 'light_4', 'light_5', 'light_6', 'light_7', 'light_8', 'light_9']
SEQUENCE_DELAY  = 3.0   # seconds after trigger before sequence starts
SEQUENCE_STEP   = 0.4   # seconds between each light in the sequence
FLICKER_DUR     = 0.6   # how long each light flickers before staying solid
FINAL_INTENSITY = 0.06  # final intensity after flickering


class BosshallwayLight:
    """On first player entry: turn on the lights one by one with a flicker effect."""

    def start(self):
        self.triggered   = False
        self.timer       = 0.0
        self.state       = 'WAITING'   # WAITING → DELAY → SEQUENCE → DONE
        self.seq_index   = 0
        self.flicker_map = {} # {light_object: time_remaining}

        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            phys = self.engine.physics_system
            p.setCollisionFilterGroupMask(body_id, -1, 0, 0, physicsClientId=phys.client_id)

    def _trigger_light(self, name):
        # We find ALL lights with this name (handles multiple light_1 objects)
        found_lights = [o for o in self.engine.scene_objects if o.name == name]
        if not found_lights:
            print(f'[BosshallwayLight] WARNING: {name} not found')
            return

        for light in found_lights:
            if USE_FLICKER:
                self.flicker_map[light] = FLICKER_DUR
            else:
                light.light_intensity = FINAL_INTENSITY
                light.alpha = 1.0

    def update(self, dt):
        # 1. Handle Active Flickering
        if USE_FLICKER and self.flicker_map:
            to_remove = []
            for light, time_left in self.flicker_map.items():
                time_left -= dt
                if time_left <= 0:
                    light.light_intensity = FINAL_INTENSITY
                    to_remove.append(light)
                else:
                    self.flicker_map[light] = time_left
                    # Rapidly oscillate intensity
                    light.light_intensity = random.uniform(0.0, FINAL_INTENSITY * 2.5)
            
            for light in to_remove:
                del self.flicker_map[light]

        # 2. Main State Machine
        if self.state == 'DONE' and not self.flicker_map:
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

            # Player entered — start the sequence
            self.timer = 0.0
            self.seq_index = 0
            self.state = 'SEQUENCE'

        elif self.state == 'SEQUENCE':
            self.timer += dt
            # Turn on every light whose turn has come
            while self.seq_index < len(SEQUENCE_LIGHTS) and \
                  self.timer >= self.seq_index * SEQUENCE_STEP:
                self._trigger_light(SEQUENCE_LIGHTS[self.seq_index])
                self.seq_index += 1

            if self.seq_index >= len(SEQUENCE_LIGHTS):
                self.state = 'DONE'
