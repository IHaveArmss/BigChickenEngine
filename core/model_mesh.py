"""ModelMesh — renders geometry loaded from OBJ or glTF files."""

import numpy as np
import glm
from mesh import Mesh
from PIL import Image


class ModelMesh(Mesh):
    """A mesh built from loaded model data (OBJ or glTF).

    Expects a mesh_data dict with:
        - vertices: np.ndarray (interleaved pos+normal+uv)
        - indices: np.ndarray or None
        - color: (r, g, b) tuple
        - texture_path: str or None
        - texture_image: PIL.Image or None (for glTF embedded)
    """

    def __init__(self, ctx, mesh_data, texture_loader):
        self._mesh_data = mesh_data
        self._texture_loader = texture_loader
        self._texture = None
        self.color = glm.vec3(*mesh_data.get('color', (0.8, 0.8, 0.8)))
        self._index_buffer = None
        self._vertex_count = 0

        super().__init__(ctx, program_name='phong')

        # Load texture if available
        tex_path = mesh_data.get('texture_path')
        tex_image = mesh_data.get('texture_image')

        if tex_path:
            self._texture = texture_loader.load(tex_path)
        elif tex_image:
            # glTF images: do NOT flip — glTF UV origin is top-left,
            # and OpenGL's texture(v_texcoord) samples correctly as-is
            img = tex_image.convert('RGBA')
            self._texture = texture_loader.load_from_bytes(
                img.tobytes(), img.width, img.height, 4,
                name=f'embedded_{id(mesh_data)}'
            )

    def get_vbo(self):
        data = self._mesh_data['vertices']
        self._vertex_count = len(data) // 8  # 8 floats per vert (pos3 + norm3 + uv2)
        return self.ctx.buffer(data)

    def get_vao(self):
        indices = self._mesh_data.get('indices')
        if indices is not None:
            self._index_buffer = self.ctx.buffer(indices.astype(np.uint32).tobytes())

        # Use parent's dynamic format building
        vao = super().get_vao()

        # If we have indices, we need to recreate the VAO with the index buffer
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

    def set_uniforms(self, camera, light_pos=None, light_color=None, object_color=None):
        super().set_uniforms(
            camera,
            light_pos=light_pos,
            light_color=light_color,
            object_color=object_color or self.color,
        )

        # Tell the shader whether to use texture
        has_tex = self._texture is not None
        self._set_uniform('u_use_texture', has_tex)

        if has_tex:
            self._texture.use(location=0)
            self._set_uniform('u_texture', 0)

    def destroy(self):
        if self._index_buffer:
            self._index_buffer.release()
        super().destroy()
