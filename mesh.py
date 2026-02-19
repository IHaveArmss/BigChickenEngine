import struct
import numpy as np
from pyglm import glm
from core.transform import Transform


class Mesh:
    """Base class for renderable meshes with Transform and MVP matrix support."""

    def __init__(self, ctx, program_name='phong'):
        self.ctx = ctx
        self.program = self._load_program(program_name)
        self.transform = Transform()
        self.alpha = 1.0
        self.vbo = self.get_vbo()
        self.vao = self.get_vao()

    # ------------------------------------------------------------------
    # Shader loading
    # ------------------------------------------------------------------

    def _load_program(self, shader_name):
        with open(f'shaders/{shader_name}.vert') as f:
            vertex_shader = f.read()
        with open(f'shaders/{shader_name}.frag') as f:
            fragment_shader = f.read()
        return self.ctx.program(vertex_shader=vertex_shader, fragment_shader=fragment_shader)

    # ------------------------------------------------------------------
    # Override in subclasses
    # ------------------------------------------------------------------

    def get_vbo(self):
        raise NotImplementedError("Subclass must define get_vbo()")

    def get_vertex_data_format(self):
        """Return (format_string, attribute_names) describing the interleaved layout.
        Default layout: position(3f) + normal(3f) + texcoord(2f).
        Subclasses can override this."""
        return [
            ('3f', 'in_position'),
            ('3f', 'in_normal'),
            ('2f', 'in_texcoord'),
        ]

    def get_vao(self):
        # Build the format dynamically — skip attributes that got optimized out
        layout = self.get_vertex_data_format()
        parts = []
        attrs = []
        for fmt, name in layout:
            if name in self.program:
                parts.append(fmt)
                attrs.append(name)
            else:
                # Attribute was optimized out — pad over those bytes.
                # 'Nf' = N * 4 bytes, so we need (N*4)x bytes of padding
                count = int(fmt.replace('f', ''))
                parts.append(f'{count * 4}x')
        combined_fmt = ' '.join(parts)
        return self.ctx.vertex_array(
            self.program,
            [(self.vbo, combined_fmt, *attrs)]
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def set_uniforms(self, camera, lights=None, object_color=None):
        """Upload MVP and lighting uniforms to the shader.

        lights: list of (position, color) tuples — each a glm.vec3 pair.
        """
        model = self.transform.model_matrix()
        view = camera.view_matrix()
        aspect = self.ctx.screen.width / self.ctx.screen.height
        proj = camera.projection_matrix(aspect)

        self._set_uniform('u_model', model)
        self._set_uniform('u_view', view)
        self._set_uniform('u_projection', proj)

        # Multi-light uniforms — moderngl requires setting ALL array
        # elements at once, so we pad unused slots with zeros
        MAX_LIGHTS = 8
        if lights:
            num = min(len(lights), MAX_LIGHTS)
            self._set_uniform('u_num_lights', num)
            pos_values = [(lp.x, lp.y, lp.z) for lp, lc in lights[:num]]
            col_values = [(lc.x, lc.y, lc.z) for lp, lc in lights[:num]]
            # Pad to full array length
            pos_values += [(0.0, 0.0, 0.0)] * (MAX_LIGHTS - num)
            col_values += [(0.0, 0.0, 0.0)] * (MAX_LIGHTS - num)
            if 'u_light_pos' in self.program:
                self.program['u_light_pos'].value = pos_values
            if 'u_light_color' in self.program:
                self.program['u_light_color'].value = col_values
        else:
            self._set_uniform('u_num_lights', 0)

        if object_color is not None:
            self._set_uniform('u_object_color', object_color)

        self._set_uniform('u_view_pos', camera.position)
        self._set_uniform('u_alpha', self.alpha)

        # Default: no texture (subclasses like ModelMesh override this)
        self._set_uniform('u_use_texture', False)

    def _set_uniform(self, name, value):
        """Safely set a uniform — silently skip if it doesn't exist in the program."""
        if name not in self.program:
            return

        if isinstance(value, glm.mat4):
            self.program[name].write(value.to_bytes())
        elif isinstance(value, glm.vec3):
            self.program[name].value = (value.x, value.y, value.z)
        else:
            self.program[name].value = value

    def render(self):
        self.vao.render()

    def update(self, dt):
        """Override for per-frame logic."""
        pass

    def destroy(self):
        self.vbo.release()
        self.program.release()
        self.vao.release()