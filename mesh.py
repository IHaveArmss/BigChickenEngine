import numpy as np
import glm
from core.transform import Transform


class Mesh:
    """Base class for renderable meshes with Transform and MVP matrix support."""

    def __init__(self, ctx, program_name='phong', shader_cache=None):
        self.ctx = ctx
        self._shader_cache = shader_cache
        self.program = self._load_program(program_name)
        self.transform = Transform()
        self.visual_offset = glm.vec3(0, 0, 0)
        self.alpha = 1.0
        self.vbo = self.get_vbo()
        self.vao = self.get_vao()

    def _load_program(self, shader_name):
        if self._shader_cache is not None:
            return self._shader_cache.get(shader_name)
        
        with open(f'shaders/{shader_name}.vert') as f:
            vs = f.read()
        with open(f'shaders/{shader_name}.frag') as f:
            fs = f.read()
        return self.ctx.program(vertex_shader=vs, fragment_shader=fs)

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
        """Upload MVP and lighting uniforms to the shader.

        lights: list of (position, color) tuples — each a glm.vec3 pair.
        """
        prog = self.program  # local ref avoids repeated attribute lookups
        _set = self._set_uniform

        model = self.transform.model_matrix()
        if hasattr(self, 'visual_offset') and glm.length(self.visual_offset) > 1e-6:
            model = model * glm.translate(glm.mat4(1.0), self.visual_offset)

        view = camera.view_matrix()
        aspect = self.ctx.screen.width / self.ctx.screen.height
        proj = camera.projection_matrix(aspect)

        _set('u_model', model)
        _set('u_view', view)
        _set('u_projection', proj)

        model_3x3 = glm.mat3(model)
        normal_matrix = glm.transpose(glm.inverse(model_3x3))
        nm_list = [normal_matrix[0][0], normal_matrix[0][1], normal_matrix[0][2],
                   normal_matrix[1][0], normal_matrix[1][1], normal_matrix[1][2],
                   normal_matrix[2][0], normal_matrix[2][1], normal_matrix[2][2]]
        _set('u_normal_matrix', nm_list)

        # Multi-light uniforms — moderngl requires setting ALL array
        # elements at once, so we pad unused slots with zeros
        MAX_LIGHTS = 8
        _ZERO3 = (0.0, 0.0, 0.0)
        if lights:
            num = min(len(lights), MAX_LIGHTS)
            _set('u_num_lights', num)
            pos_values = [(lp.x, lp.y, lp.z) for lp, lc in lights[:num]]
            col_values = [(lc.x, lc.y, lc.z) for lp, lc in lights[:num]]
            # Pad to full array length
            pad = MAX_LIGHTS - num
            if pad > 0:
                pos_values += [_ZERO3] * pad
                col_values += [_ZERO3] * pad
            if 'u_light_pos' in prog:
                prog['u_light_pos'].value = pos_values
            if 'u_light_color' in prog:
                prog['u_light_color'].value = col_values
        else:
            _set('u_num_lights', 0)

        if object_color is not None:
            _set('u_object_color', object_color)

        _set('u_view_pos', camera.position)
        _set('u_alpha', self.alpha)

        # Default: no texture (subclasses like ModelMesh override this)
        _set('u_use_texture', False)

        # Optional retro/PS2 settings (silently ignored by shaders that don't use them)
        rs = render_settings
        if rs is not None:
            _set('u_ps2_enabled', bool(getattr(rs, 'ps2_enabled', False)))
            _set('u_lighting_ramp_enabled', bool(getattr(rs, 'lighting_ramp_enabled', True)))
            _set('u_lighting_ramp_steps', int(max(1, getattr(rs, 'lighting_ramp_steps', 4))))
            _set('u_specular_banding_enabled', bool(getattr(rs, 'specular_banding_enabled', False)))
            _set('u_specular_steps', int(max(1, getattr(rs, 'specular_steps', 3))))
            _set('u_wobble_enabled', bool(getattr(rs, 'wobble_enabled', False)))
            _set('u_wobble_pixel_size', int(max(1, getattr(rs, 'wobble_pixel_size', 2))))

        if viewport is not None:
            if 'u_viewport' in prog:
                prog['u_viewport'].value = (float(viewport[0]), float(viewport[1]))
        if dir_light_vp is not None:
            _set('u_dir_light_vp', dir_light_vp)
        _set('u_receives_shadows', bool(receives_shadows))

        if rs is not None:
            _set('u_directional_shadows_enabled', bool(getattr(rs, 'directional_shadows_enabled', False)))
            _set('u_shadow_bias', float(getattr(rs, 'shadow_bias', 0.0015)))
            ambient = glm.vec3(
                float(getattr(rs, 'ambient_color_r', 1.0)),
                float(getattr(rs, 'ambient_color_g', 1.0)),
                float(getattr(rs, 'ambient_color_b', 1.0)),
            )
            _set('u_ambient_color', ambient)
            _set('u_ambient_strength', float(getattr(rs, 'ambient_strength', 0.15)))

        _set('u_highlight_strength', float(highlight_strength))
        color = highlight_color if highlight_color is not None else (1.0, 0.85, 0.2)
        _set('u_highlight_color', glm.vec3(*color))

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
        self.vao.release()