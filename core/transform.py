import glm


class Transform:
    """Represents position, rotation, and scale of an object in 3D space."""

    def __init__(self, position=None, rotation=None, scale=None):
        self.position = position if position is not None else glm.vec3(0.0)
        self.rotation = rotation if rotation is not None else glm.quat()  # identity
        self.scale = scale if scale is not None else glm.vec3(1.0)

    def model_matrix(self) -> glm.mat4:
        """Compute the TRS (Translate * Rotate * Scale) model matrix."""
        m = glm.mat4(1.0)
        m = glm.translate(m, self.position)
        m = m * glm.mat4_cast(self.rotation)
        m = glm.scale(m, self.scale)
        return m

    def forward(self) -> glm.vec3:
        """Return the local -Z direction in world space (OpenGL convention)."""
        return glm.normalize(self.rotation * glm.vec3(0.0, 0.0, -1.0))

    def right(self) -> glm.vec3:
        """Return the local +X direction in world space."""
        return glm.normalize(self.rotation * glm.vec3(1.0, 0.0, 0.0))

    def up(self) -> glm.vec3:
        """Return the local +Y direction in world space."""
        return glm.normalize(self.rotation * glm.vec3(0.0, 1.0, 0.0))

    def rotate_euler(self, pitch_deg=0.0, yaw_deg=0.0, roll_deg=0.0):
        """Apply an incremental rotation from Euler angles (degrees)."""
        q = glm.quat(glm.vec3(
            glm.radians(pitch_deg),
            glm.radians(yaw_deg),
            glm.radians(roll_deg),
        ))
        self.rotation = q * self.rotation
