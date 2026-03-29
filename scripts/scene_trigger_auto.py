import pybullet as p


class SceneTriggerAuto:
    """Loads a scene when the player walks into this trigger volume.
    Set 'scene_path' on the object in the scene JSON to choose the target scene.
    Optionally set 'target_position' and 'target_rotation' for a spawn override."""

    def start(self):
        self._triggered = False
        self._timer     = 0.0
        self._delay     = 5.0

        body_id = getattr(self.entity, 'pybullet_body_id', None)
        if body_id is not None:
            p.setCollisionFilterGroupMask(body_id, -1, 0, 0,
                                          physicsClientId=self.engine.physics_system.client_id)

    def update(self, dt):
        if self._triggered:
            self._timer += dt
            if self._timer >= self._delay:
                self._do_load()
            return

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

    def _do_load(self):
        target    = getattr(self.entity, 'scene_path', None)
        spawn_pos = getattr(self.entity, 'target_position', None)
        spawn_rot = getattr(self.entity, 'target_rotation', None)
        
        task_title = getattr(self.entity, 'task_title', None)
        task_desc  = getattr(self.entity, 'task_desc', None)

        if not target:
            print("[SceneTriggerAuto] No scene_path set on trigger object")
            return

        if task_title or task_desc:
            print(f"[SceneTriggerAuto] Setting task: {task_title} - {task_desc}")
            self.engine.hud.set_task(task_title or "", task_desc or "")

        self.engine.load_scene(target, spawn_pos=spawn_pos, spawn_rot=spawn_rot)
