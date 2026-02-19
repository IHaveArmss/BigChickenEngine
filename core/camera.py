from pyglm import glm
import pygame


class Camera:
    """FPS-style camera with mouse-look and WASD movement."""

    def __init__(self, position=None, yaw=-90.0, pitch=0.0):
        self.position = position if position is not None else glm.vec3(0.0, 1.0, 3.0)
        self.yaw = yaw      # degrees, -90 = looking along -Z
        self.pitch = pitch   # degrees

        self.fov = 60.0       # vertical FOV in degrees
        self.near = 0.1
        self.far = 100.0
        self.speed = 5.0      # units per second
        self.sensitivity = 0.1  # degrees per pixel of mouse movement

        # Cached direction vectors (recomputed every frame)
        self.front = glm.vec3(0.0, 0.0, -1.0)
        self.right = glm.vec3(1.0, 0.0, 0.0)
        self.up = glm.vec3(0.0, 1.0, 0.0)
        self._update_vectors()

    # ------------------------------------------------------------------
    # Matrices
    # ------------------------------------------------------------------

    def view_matrix(self) -> glm.mat4:
        return glm.lookAt(self.position, self.position + self.front, self.up)

    def projection_matrix(self, aspect_ratio: float) -> glm.mat4:
        return glm.perspective(glm.radians(self.fov), aspect_ratio, self.near, self.far)

    # ------------------------------------------------------------------
    # Input processing
    # ------------------------------------------------------------------

    def process_mouse(self, dx: float, dy: float):
        """Update yaw/pitch from mouse delta (pixels)."""
        self.yaw += dx * self.sensitivity
        self.pitch -= dy * self.sensitivity  # inverted Y
        self.pitch = max(-89.0, min(89.0, self.pitch))
        self._update_vectors()

    def process_keyboard(self, dt: float):
        """Move camera based on currently held keys."""
        keys = pygame.key.get_pressed()
        velocity = self.speed * dt

        if keys[pygame.K_w]:
            self.position += self.front * velocity
        if keys[pygame.K_s]:
            self.position -= self.front * velocity
        if keys[pygame.K_a]:
            self.position -= self.right * velocity
        if keys[pygame.K_d]:
            self.position += self.right * velocity
        if keys[pygame.K_SPACE]:
            self.position += glm.vec3(0.0, 1.0, 0.0) * velocity
        if keys[pygame.K_LSHIFT]:
            self.position -= glm.vec3(0.0, 1.0, 0.0) * velocity

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_vectors(self):
        """Recalculate front/right/up from yaw and pitch."""
        rad_yaw = glm.radians(self.yaw)
        rad_pitch = glm.radians(self.pitch)

        self.front = glm.normalize(glm.vec3(
            glm.cos(rad_yaw) * glm.cos(rad_pitch),
            glm.sin(rad_pitch),
            glm.sin(rad_yaw) * glm.cos(rad_pitch),
        ))
        self.right = glm.normalize(glm.cross(self.front, glm.vec3(0.0, 1.0, 0.0)))
        self.up = glm.normalize(glm.cross(self.right, self.front))
