"""ModelMesh — renders geometry loaded from OBJ or glTF files, with optional skeletal skinning."""

import numpy as np
import glm
from mesh import Mesh
from PIL import Image
from core.animator import MAX_BONES


class ModelMesh(Mesh):
    """A mesh built from loaded model data (OBJ or glTF).

    Expects a mesh_data dict with:
        - vertices: np.ndarray (interleaved pos+normal+uv, optionally +joints+weights)
        - indices: np.ndarray or None
        - color: (r, g, b) tuple
        - texture_path: str or None
        - texture_image: PIL.Image or None (for glTF embedded)
        - has_skin: bool (optional)
    """

    def __init__(self, ctx, mesh_data, texture_loader):
        self._mesh_data = mesh_data
        self._texture_loader = texture_loader
        self._texture = None
        self.color = glm.vec3(*mesh_data.get('color', (0.8, 0.8, 0.8)))
        self._index_buffer = None
        self._vertex_count = 0
        self._has_skin = mesh_data.get('has_skin', False)
        self.animator = None

        super().__init__(ctx, program_name='phong')

        tex_path = mesh_data.get('texture_path')
        tex_image = mesh_data.get('texture_image')

        if tex_path:
            self._texture = texture_loader.load(tex_path)
        elif tex_image:
            img = tex_image.convert('RGBA')
            self._texture = texture_loader.load_from_bytes(
                img.tobytes(), img.width, img.height, 4,
                name=f'embedded_{id(mesh_data)}'
            )

    def _load_program(self, shader_name):
        if self._has_skin:
            vert_name, frag_name = 'phong_skinned', 'phong'
        else:
            vert_name, frag_name = shader_name, shader_name
        with open(f'shaders/{vert_name}.vert') as f:
            vs = f.read()
        with open(f'shaders/{frag_name}.frag') as f:
            fs = f.read()
        return self.ctx.program(vertex_shader=vs, fragment_shader=fs)

    def get_vertex_data_format(self):
        base = [
            ('3f', 'in_position'),
            ('3f', 'in_normal'),
            ('2f', 'in_texcoord'),
        ]
        if self._has_skin:
            base.append(('4f', 'in_joints'))
            base.append(('4f', 'in_weights'))
        return base

    def get_vbo(self):
        data = self._mesh_data['vertices']
        floats_per_vert = 16 if self._has_skin else 8
        self._vertex_count = len(data) // floats_per_vert
        return self.ctx.buffer(data)

    def get_vao(self):
        indices = self._mesh_data.get('indices')
        if indices is not None:
            self._index_buffer = self.ctx.buffer(indices.astype(np.uint32).tobytes())

        vao = super().get_vao()

        if self._index_buffer is not None:
            vao.release()
            layout = self.get_vertex_data_format()
            parts = []
            attrs = []
            for fmt, name in layout:
                if name in self.program:
                    parts.append(fmt)
                    attrs.append(name)
                else:
                    count = int(fmt.replace('f', ''))
                    parts.append(f'{count * 4}x')
            combined_fmt = ' '.join(parts)
            vao = self.ctx.vertex_array(
                self.program,
                [(self.vbo, combined_fmt, *attrs)],
                self._index_buffer,
            )
        return vao

    def set_uniforms(
        self,
        camera,
        lights=None,
        object_color=None,
        render_settings=None,
        viewport=None,
        dir_light_vp=None,
        receives_shadows=True,
    ):
        super().set_uniforms(
            camera,
            lights=lights,
            object_color=object_color or self.color,
            render_settings=render_settings,
            viewport=viewport,
            dir_light_vp=dir_light_vp,
            receives_shadows=receives_shadows,
        )

        has_tex = self._texture is not None
        self._set_uniform('u_use_texture', has_tex)

        if has_tex:
            self._texture.use(location=0)
            self._set_uniform('u_texture', 0)

        if self._has_skin and self.animator is not None:
            if 'u_bone_matrices' in self.program:
                bone_data = self.animator.bone_bytes
                n = self.animator.num_bones
                pad = MAX_BONES - n
                if pad > 0:
                    bone_data += b''.join(glm.mat4(1.0).to_bytes() for _ in range(pad))
                self.program['u_bone_matrices'].write(bone_data)

    def destroy(self):
        if self._index_buffer:
            self._index_buffer.release()
        super().destroy()
