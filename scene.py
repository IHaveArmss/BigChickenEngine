import numpy as np
import glm
from mesh import Mesh


class Cube(Mesh):
    """A unit cube with per-face normals for Phong shading."""

    def __init__(self, ctx, color=None, shader_cache=None):
        self.color = color if color is not None else glm.vec3(0.49, 0.48, 1.0)
        super().__init__(ctx, program_name='phong', shader_cache=shader_cache)

    def get_vbo(self):
        # Each face = 2 triangles = 6 vertices
        # Each vertex = position(3) + normal(3) + texcoord(2) = 8 floats
        vertices = np.array([
            # Front face (normal 0, 0, 1)
            -0.5, -0.5,  0.5,  0.0,  0.0,  1.0,  0.0, 0.0,
             0.5, -0.5,  0.5,  0.0,  0.0,  1.0,  1.0, 0.0,
             0.5,  0.5,  0.5,  0.0,  0.0,  1.0,  1.0, 1.0,
            -0.5, -0.5,  0.5,  0.0,  0.0,  1.0,  0.0, 0.0,
             0.5,  0.5,  0.5,  0.0,  0.0,  1.0,  1.0, 1.0,
            -0.5,  0.5,  0.5,  0.0,  0.0,  1.0,  0.0, 1.0,

            # Back face (normal 0, 0, -1)
             0.5, -0.5, -0.5,  0.0,  0.0, -1.0,  0.0, 0.0,
            -0.5, -0.5, -0.5,  0.0,  0.0, -1.0,  1.0, 0.0,
            -0.5,  0.5, -0.5,  0.0,  0.0, -1.0,  1.0, 1.0,
             0.5, -0.5, -0.5,  0.0,  0.0, -1.0,  0.0, 0.0,
            -0.5,  0.5, -0.5,  0.0,  0.0, -1.0,  1.0, 1.0,
             0.5,  0.5, -0.5,  0.0,  0.0, -1.0,  0.0, 1.0,

            # Top face (normal 0, 1, 0)
            -0.5,  0.5,  0.5,  0.0,  1.0,  0.0,  0.0, 0.0,
             0.5,  0.5,  0.5,  0.0,  1.0,  0.0,  1.0, 0.0,
             0.5,  0.5, -0.5,  0.0,  1.0,  0.0,  1.0, 1.0,
            -0.5,  0.5,  0.5,  0.0,  1.0,  0.0,  0.0, 0.0,
             0.5,  0.5, -0.5,  0.0,  1.0,  0.0,  1.0, 1.0,
            -0.5,  0.5, -0.5,  0.0,  1.0,  0.0,  0.0, 1.0,

            # Bottom face (normal 0, -1, 0)
            -0.5, -0.5, -0.5,  0.0, -1.0,  0.0,  0.0, 0.0,
             0.5, -0.5, -0.5,  0.0, -1.0,  0.0,  1.0, 0.0,
             0.5, -0.5,  0.5,  0.0, -1.0,  0.0,  1.0, 1.0,
            -0.5, -0.5, -0.5,  0.0, -1.0,  0.0,  0.0, 0.0,
             0.5, -0.5,  0.5,  0.0, -1.0,  0.0,  1.0, 1.0,
            -0.5, -0.5,  0.5,  0.0, -1.0,  0.0,  0.0, 1.0,

            # Right face (normal 1, 0, 0)
             0.5, -0.5,  0.5,  1.0,  0.0,  0.0,  0.0, 0.0,
             0.5, -0.5, -0.5,  1.0,  0.0,  0.0,  1.0, 0.0,
             0.5,  0.5, -0.5,  1.0,  0.0,  0.0,  1.0, 1.0,
             0.5, -0.5,  0.5,  1.0,  0.0,  0.0,  0.0, 0.0,
             0.5,  0.5, -0.5,  1.0,  0.0,  0.0,  1.0, 1.0,
             0.5,  0.5,  0.5,  1.0,  0.0,  0.0,  0.0, 1.0,

            # Left face (normal -1, 0, 0)
            -0.5, -0.5, -0.5, -1.0,  0.0,  0.0,  0.0, 0.0,
            -0.5, -0.5,  0.5, -1.0,  0.0,  0.0,  1.0, 0.0,
            -0.5,  0.5,  0.5, -1.0,  0.0,  0.0,  1.0, 1.0,
            -0.5, -0.5, -0.5, -1.0,  0.0,  0.0,  0.0, 0.0,
            -0.5,  0.5,  0.5, -1.0,  0.0,  0.0,  1.0, 1.0,
            -0.5,  0.5, -0.5, -1.0,  0.0,  0.0,  0.0, 1.0,
        ], dtype='f4')

        return self.ctx.buffer(vertices)

    def set_uniforms(
        self,
        camera,
        lights=None,
        object_color=None,
        render_settings=None,
        viewport=None,
        dir_light_vp=None,
        receives_shadows=True,
        highlight_strength=0.0,
        highlight_color=None,
    ):
        super().set_uniforms(
            camera,
            lights=lights,
            object_color=object_color or self.color,
            render_settings=render_settings,
            viewport=viewport,
            dir_light_vp=dir_light_vp,
            receives_shadows=receives_shadows,
            highlight_strength=highlight_strength,
            highlight_color=highlight_color,
        )



class Triangle(Mesh):
    """A simple triangle primitive for scene building."""

    def __init__(self, ctx, color=None, shader_cache=None):
        self.color = color if color is not None else glm.vec3(1.0, 0.4, 0.2)
        super().__init__(ctx, program_name='phong', shader_cache=shader_cache)

    def get_vbo(self):
        # Equilateral triangle lying on XZ plane, pointing up along Y
        vertices = np.array([
            # pos(3)              normal(3)           uv(2)
             0.0,  0.5,  0.0,    0.0,  0.0,  1.0,   0.5, 1.0,
            -0.5, -0.5,  0.0,    0.0,  0.0,  1.0,   0.0, 0.0,
             0.5, -0.5,  0.0,    0.0,  0.0,  1.0,   1.0, 0.0,
            # Back face
             0.0,  0.5,  0.0,    0.0,  0.0, -1.0,   0.5, 1.0,
             0.5, -0.5,  0.0,    0.0,  0.0, -1.0,   1.0, 0.0,
            -0.5, -0.5,  0.0,    0.0,  0.0, -1.0,   0.0, 0.0,
        ], dtype='f4')
        return self.ctx.buffer(vertices)

    def set_uniforms(
        self,
        camera,
        lights=None,
        object_color=None,
        render_settings=None,
        viewport=None,
        dir_light_vp=None,
        receives_shadows=True,
        highlight_strength=0.0,
        highlight_color=None,
    ):
        super().set_uniforms(
            camera,
            lights=lights,
            object_color=object_color or self.color,
            render_settings=render_settings,
            viewport=viewport,
            dir_light_vp=dir_light_vp,
            receives_shadows=receives_shadows,
            highlight_strength=highlight_strength,
            highlight_color=highlight_color,
        )


class GridFloor(Mesh):
    """A flat grid on the XZ plane to give spatial reference."""

    def __init__(self, ctx, size=10, step=1.0):
        self.grid_size = size
        self.grid_step = step
        self.color = glm.vec3(0.35, 0.35, 0.4)
        super().__init__(ctx, program_name='phong')
        # Tell the frustum culler our true world-space extent.
        # The floor's farthest corner is sqrt(2)*size from origin.
        # Without this, scale=(1,1,1) gives cull radius=0.866 and the whole
        # floor vanishes whenever the camera looks away from origin.
        import math as _math
        self.bounding_radius = _math.sqrt(2.0) * size

    def get_vbo(self):
        """Build a subdivided grid on the XZ plane to prevent perspective
        interpolation artifacts (floor 'teleporting') when looking around.
        Each cell is grid_step × grid_step world units."""
        s = self.grid_size
        step = self.grid_step
        verts = []

        x = -s
        while x < s - 1e-5:
            x1 = min(x + step, s)
            z = -s
            while z < s - 1e-5:
                z1 = min(z + step, s)

                # Normalised UVs for this cell
                u0 = (x + s) / (2.0 * s)
                u1 = (x1 + s) / (2.0 * s)
                v0 = (z + s) / (2.0 * s)
                v1 = (z1 + s) / (2.0 * s)

                # Two triangles, pos(3) + normal(3) + uv(2) per vertex
                # Triangle 1
                verts.extend([x,  0.0, z,   0.0, 1.0, 0.0,  u0, v0])
                verts.extend([x1, 0.0, z,   0.0, 1.0, 0.0,  u1, v0])
                verts.extend([x1, 0.0, z1,  0.0, 1.0, 0.0,  u1, v1])
                # Triangle 2
                verts.extend([x,  0.0, z,   0.0, 1.0, 0.0,  u0, v0])
                verts.extend([x1, 0.0, z1,  0.0, 1.0, 0.0,  u1, v1])
                verts.extend([x,  0.0, z1,  0.0, 1.0, 0.0,  u0, v1])

                z += step
            x += step

        return self.ctx.buffer(np.array(verts, dtype='f4'))

    def set_uniforms(
        self,
        camera,
        lights=None,
        object_color=None,
        render_settings=None,
        viewport=None,
        dir_light_vp=None,
        receives_shadows=True,
        highlight_strength=0.0,
        highlight_color=None,
    ):
        super().set_uniforms(
            camera,
            lights=lights,
            object_color=object_color or self.color,
            render_settings=render_settings,
            viewport=viewport,
            dir_light_vp=dir_light_vp,
            receives_shadows=receives_shadows,
            highlight_strength=highlight_strength,
            highlight_color=highlight_color,
        )


class LightOrb(Mesh):
    """A small sphere that marks the light source position. Uses unlit shader."""

    def __init__(self, ctx, radius=0.15, color=None, shader_cache=None):
        self.orb_radius = radius
        self.color = color if color is not None else glm.vec3(1.0, 1.0, 0.7)
        self._vertex_count = 0
        super().__init__(ctx, program_name='unlit', shader_cache=shader_cache)

    def get_vertex_data_format(self):
        # Unlit shader only needs position
        return [
            ('3f', 'in_position'),
        ]

    def get_vbo(self):
        """Generate a UV sphere with position-only vertices."""
        stacks = 10
        sectors = 16
        r = self.orb_radius
        verts = []

        for i in range(stacks):
            lat0 = np.pi * (-0.5 + i / stacks)
            lat1 = np.pi * (-0.5 + (i + 1) / stacks)
            y0, yr0 = np.sin(lat0) * r, np.cos(lat0) * r
            y1, yr1 = np.sin(lat1) * r, np.cos(lat1) * r

            for j in range(sectors):
                lon0 = 2.0 * np.pi * j / sectors
                lon1 = 2.0 * np.pi * (j + 1) / sectors

                x00, z00 = np.cos(lon0) * yr0, np.sin(lon0) * yr0
                x10, z10 = np.cos(lon1) * yr0, np.sin(lon1) * yr0
                x01, z01 = np.cos(lon0) * yr1, np.sin(lon0) * yr1
                x11, z11 = np.cos(lon1) * yr1, np.sin(lon1) * yr1

                # Two triangles per quad
                verts.extend([x00, y0, z00,  x01, y1, z01,  x10, y0, z10])
                verts.extend([x10, y0, z10,  x01, y1, z01,  x11, y1, z11])

        self._vertex_count = len(verts) // 3
        return self.ctx.buffer(np.array(verts, dtype='f4'))

    def set_uniforms(self, camera, lights=None, object_color=None, render_settings=None, viewport=None, **kwargs):
        """Position the orb at the light location. Unlit — ignores lights."""
        model = self.transform.model_matrix()
        view = camera.view_matrix()
        aspect = camera_aspect(self.ctx)
        proj = camera.projection_matrix(aspect)

        self._set_uniform('u_model', model)
        self._set_uniform('u_view', view)
        self._set_uniform('u_projection', proj)
        self._set_uniform('u_object_color', object_color or self.color)


def camera_aspect(ctx):
    """Helper to compute aspect ratio from the ModernGL context."""
    return ctx.screen.width / ctx.screen.height