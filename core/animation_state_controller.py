"""AnimationStateController - simple clip state machine for characters."""

import pybullet as p
import glm


class AnimationStateController:
    """Drives animator states (idle/run/jump/fall) from motion heuristics."""

    def __init__(
        self,
        animator,
        idle_clip='idle',
        run_clip='run',
        jump_clip='jump',
        fall_clip='fall',
        move_threshold=0.1,
        vertical_threshold=0.15,
    ):
        self.animator = animator
        self.idle_clip = idle_clip
        self.run_clip = run_clip
        self.jump_clip = jump_clip
        self.fall_clip = fall_clip
        self.move_threshold = move_threshold
        self.vertical_threshold = vertical_threshold

        self._resolved = {}
        self._current_state = None
        self._last_pos = None
        self._resolve_clips()
        self._play_initial()

    def _resolve_clips(self):
        names = self.animator.clip_names
        self._resolved = {
            'idle': _resolve_clip_name(names, self.idle_clip, 'idle'),
            'run': _resolve_clip_name(names, self.run_clip, 'run'),
            'jump': _resolve_clip_name(names, self.jump_clip, 'jump'),
            'fall': _resolve_clip_name(names, self.fall_clip, 'fall'),
        }

    def _play_initial(self):
        clip = self._resolved.get('idle') or self._resolved.get('run')
        if clip:
            self.animator.play(clip, loop=True)
            self._current_state = 'idle' if self._resolved.get('idle') else 'run'

    def update(self, dt, obj=None, physics_system=None):
        if self.animator is None:
            return

        self._resolve_clips()

        vx, vy, vz = self._sample_velocity(dt, obj, physics_system)
        horizontal_speed = (vx * vx + vz * vz) ** 0.5

        next_state = 'idle'
        if vy > self.vertical_threshold and self._resolved.get('jump'):
            next_state = 'jump'
        elif vy < -self.vertical_threshold and self._resolved.get('fall'):
            next_state = 'fall'
        elif horizontal_speed > self.move_threshold and self._resolved.get('run'):
            next_state = 'run'
        elif self._resolved.get('idle'):
            next_state = 'idle'
        elif self._resolved.get('run'):
            next_state = 'run'

        if next_state != self._current_state:
            clip_name = self._resolved.get(next_state)
            if clip_name:
                self.animator.crossfade(clip_name, duration=0.18, loop=True)
                self._current_state = next_state

    def _sample_velocity(self, dt, obj, physics_system):
        if obj is not None and physics_system is not None:
            body_id = getattr(obj, 'pybullet_body_id', None)
            is_kinematic = getattr(obj, 'is_kinematic', True)
            if body_id is not None and not is_kinematic:
                lin_vel, _ = p.getBaseVelocity(body_id, physicsClientId=physics_system.client_id)
                return float(lin_vel[0]), float(lin_vel[1]), float(lin_vel[2])

        if obj is None or dt <= 0:
            return 0.0, 0.0, 0.0

        pos = glm.vec3(obj.position)
        if self._last_pos is None:
            self._last_pos = glm.vec3(pos)
            return 0.0, 0.0, 0.0

        v = (pos - self._last_pos) / max(dt, 1e-6)
        self._last_pos = glm.vec3(pos)
        return float(v.x), float(v.y), float(v.z)

    def to_dict(self):
        return {
            'idle': self.idle_clip,
            'run': self.run_clip,
            'jump': self.jump_clip,
            'fall': self.fall_clip,
            'move_threshold': float(self.move_threshold),
            'vertical_threshold': float(self.vertical_threshold),
        }


def _resolve_clip_name(available, preferred, fallback_keyword):
    if not available:
        return None

    if preferred and preferred in available:
        return preferred

    wanted = (preferred or fallback_keyword or '').lower()
    for name in available:
        if wanted and wanted in name.lower():
            return name

    if fallback_keyword:
        key = fallback_keyword.lower()
        for name in available:
            if key in name.lower():
                return name

    return available[0]
