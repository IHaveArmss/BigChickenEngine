"""Skeletal animation system — Skeleton, AnimationClip, and Animator."""

import glm
import numpy as np

MAX_BONES = 64


class Channel:
    """A single animated property (translation/rotation/scale) for one bone."""

    __slots__ = ('bone_index', 'path', 'times', 'values', 'interpolation')

    def __init__(self, bone_index, path, times, values, interpolation='LINEAR'):
        self.bone_index = bone_index
        self.path = path
        self.times = times
        self.values = values
        self.interpolation = interpolation

    def sample(self, t):
        times = self.times
        values = self.values
        n = len(times)
        if n == 0:
            return _default_for_path(self.path)
        if n == 1 or t <= times[0]:
            return values[0]
        if t >= times[-1]:
            return values[-1]

        idx = int(np.searchsorted(times, t, side='right')) - 1
        idx = max(0, min(idx, n - 2))

        t0, t1 = times[idx], times[idx + 1]
        factor = (t - t0) / (t1 - t0) if t1 > t0 else 0.0

        v0, v1 = values[idx], values[idx + 1]

        if self.interpolation == 'STEP':
            return v0

        if self.path == 'rotation':
            return glm.slerp(v0, v1, factor)
        return glm.mix(v0, v1, factor)


class AnimationClip:
    """A named animation containing channels for various bones."""

    def __init__(self, name, duration, channels):
        self.name = name
        self.duration = duration
        self.channels = channels


class Skeleton:
    """Bone hierarchy with bind-pose data."""

    def __init__(self, joint_names, parent_indices, inverse_bind_matrices,
                 bind_translations, bind_rotations, bind_scales):
        self.joint_names = joint_names
        self.parent_indices = parent_indices
        self.inverse_bind_matrices = inverse_bind_matrices
        self.bind_translations = bind_translations
        self.bind_rotations = bind_rotations
        self.bind_scales = bind_scales
        self.num_joints = len(joint_names)


class Animator:
    """Drives skeletal animation playback on a SceneObject.

    Usage from scripts:
        self.entity.animator.play("run")
        self.entity.animator.crossfade("idle", 0.3)
    """

    def __init__(self, skeleton, animations):
        self.skeleton = skeleton
        self.animations = animations
        self.current_clip = None
        self.time = 0.0
        self.playing = False
        self.looping = True
        self.speed = 1.0

        n = min(skeleton.num_joints, MAX_BONES)
        self._bone_matrices = [glm.mat4(1.0)] * n
        self._bone_bytes = b'\x00' * (n * 64)

        self._blend_clip = None
        self._blend_time = 0.0
        self._blend_duration = 0.0
        self._blend_elapsed = 0.0

    @property
    def clip_names(self):
        return list(self.animations.keys())

    @property
    def is_playing(self):
        return self.playing

    def play(self, name, loop=True, speed=1.0):
        clip = self.animations.get(name)
        if clip is None:
            print(f"[Animator] WARNING: clip '{name}' not found. Available: {self.clip_names}")
            return
        self._blend_clip = None
        self.current_clip = clip
        self.time = 0.0
        self.playing = True
        self.looping = loop
        self.speed = speed

    def crossfade(self, name, duration=0.3, loop=True, speed=1.0):
        clip = self.animations.get(name)
        if clip is None:
            print(f"[Animator] WARNING: clip '{name}' not found.")
            return
        if self.current_clip is clip:
            return
        self._blend_clip = self.current_clip
        self._blend_time = self.time
        self._blend_duration = max(duration, 0.001)
        self._blend_elapsed = 0.0
        self.current_clip = clip
        self.time = 0.0
        self.playing = True
        self.looping = loop
        self.speed = speed

    def stop(self):
        self.playing = False

    def update(self, dt):
        if not self.playing or self.current_clip is None:
            return

        self.time += dt * self.speed
        clip = self.current_clip

        if self.looping and clip.duration > 0:
            self.time = self.time % clip.duration
        elif self.time >= clip.duration:
            self.time = clip.duration
            self.playing = False

        skel = self.skeleton
        n = min(skel.num_joints, MAX_BONES)

        t_a = list(skel.bind_translations)
        r_a = list(skel.bind_rotations)
        s_a = list(skel.bind_scales)
        _apply_clip(clip, self.time, t_a, r_a, s_a)

        if self._blend_clip is not None:
            self._blend_elapsed += dt
            blend_factor = min(self._blend_elapsed / self._blend_duration, 1.0)

            if blend_factor >= 1.0:
                self._blend_clip = None
            else:
                prev = self._blend_clip
                self._blend_time += dt * self.speed
                if prev.duration > 0:
                    self._blend_time = self._blend_time % prev.duration

                t_b = list(skel.bind_translations)
                r_b = list(skel.bind_rotations)
                s_b = list(skel.bind_scales)
                _apply_clip(prev, self._blend_time, t_b, r_b, s_b)

                for i in range(n):
                    t_a[i] = glm.mix(t_b[i], t_a[i], blend_factor)
                    r_a[i] = glm.slerp(r_b[i], r_a[i], blend_factor)
                    s_a[i] = glm.mix(s_b[i], s_a[i], blend_factor)

        world = [glm.mat4(1.0)] * n
        for i in range(n):
            local = (glm.translate(glm.mat4(1.0), t_a[i])
                     * glm.mat4_cast(r_a[i])
                     * glm.scale(glm.mat4(1.0), s_a[i]))
            parent = skel.parent_indices[i]
            world[i] = (world[parent] * local) if 0 <= parent < n else local
            self._bone_matrices[i] = world[i] * skel.inverse_bind_matrices[i]

        self._bone_bytes = b''.join(m.to_bytes() for m in self._bone_matrices)

    @property
    def bone_bytes(self):
        return self._bone_bytes

    @property
    def num_bones(self):
        return len(self._bone_matrices)

    def get_root_transform(self):
        """Returns (pos, quat, scale) of the root bone (index 0)."""
        if not self._bone_matrices:
            return None, None, None
        m = self._bone_matrices[0]
        pos = glm.vec3(m[3])
        # Decompose scale
        scl = glm.vec3(
            glm.length(glm.vec3(m[0])),
            glm.length(glm.vec3(m[1])),
            glm.length(glm.vec3(m[2]))
        )
        # Decompose rotation (removing scale)
        nm = glm.mat4(m)
        if scl.x != 0: nm[0] /= scl.x
        if scl.y != 0: nm[1] /= scl.y
        if scl.z != 0: nm[2] /= scl.z
        rot = glm.quat_cast(nm)
        return pos, rot, scl


def _apply_clip(clip, t, translations, rotations, scales):
    for ch in clip.channels:
        idx = ch.bone_index
        if idx < 0 or idx >= len(translations):
            continue
        val = ch.sample(t)
        if ch.path == 'translation':
            translations[idx] = val
        elif ch.path == 'rotation':
            rotations[idx] = val
        elif ch.path == 'scale':
            scales[idx] = val


def _default_for_path(path):
    if path == 'rotation':
        return glm.quat(1.0, 0.0, 0.0, 0.0)
    if path == 'scale':
        return glm.vec3(1.0)
    return glm.vec3(0.0)
