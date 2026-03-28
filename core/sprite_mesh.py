import os
import numpy as np
import glm
from PIL import Image
from mesh import Mesh


# Global cache to reuse sprite textures and metadata
_SPRITE_CACHE = {}

def clear_sprite_cache():
    for data in _SPRITE_CACHE.values():
        if data.get('texture'):
            data['texture'].release()
    _SPRITE_CACHE.clear()


class SpriteMesh(Mesh):
    def __init__(self, ctx, texture_loader, image_path, shader_cache=None, 
                 autocrop=True, billboard=False, shader_name='textured'):
        self.image_path = image_path
        self.billboard = billboard
        self.autocrop = autocrop
        self._shader_name = shader_name
        
        abs_path = os.path.abspath(image_path)
        cache_key = (abs_path, autocrop)
        
        if cache_key in _SPRITE_CACHE:
            data = _SPRITE_CACHE[cache_key]
            self._width = data['width']
            self._height = data['height']
            self._offset_x = data['offset_x']
            self._offset_y = data['offset_y']
            self._original_width = data['original_width']
            self._original_height = data['original_height']
            self._texture = data['texture']
            print(f"[SpriteMesh] Reusing cached sprite: {image_path}")
        else:
            with Image.open(abs_path) as img:
                img = img.convert('RGBA')
                
                bbox = None
                if autocrop:
                    bbox = self._compute_autocrop_bbox(img)
                    if bbox:
                        left, top, right, bottom = bbox
                        cropped = img.crop(bbox)
                        self._width = right - left
                        self._height = bottom - top
                        self._offset_x = left
                        self._offset_y = top
                    else:
                        self._width = img.width
                        self._height = img.height
                        self._offset_x = 0
                        self._offset_y = 0
                else:
                    self._width = img.width
                    self._height = img.height
                    self._offset_x = 0
                    self._offset_y = 0
                
                self._original_width = img.width
                self._original_height = img.height
                
                img_data = np.array(cropped if autocrop and bbox else img, dtype='uint8')
                self._texture = ctx.texture((self._width, self._height), 4, img_data.tobytes())
                self._texture.filter = (ctx.LINEAR_MIPMAP_LINEAR, ctx.LINEAR)
                self._texture.build_mipmaps()
                self._texture.anisotropy = 16.0
                
                _SPRITE_CACHE[cache_key] = {
                    'width': self._width,
                    'height': self._height,
                    'offset_x': self._offset_x,
                    'offset_y': self._offset_y,
                    'original_width': self._original_width,
                    'original_height': self._original_height,
                    'texture': self._texture
                }
                print(f"[SpriteMesh] Created and cached sprite from {image_path} ({self._width}x{self._height})")

        self._aspect_ratio = ctx.screen.width / ctx.screen.height if ctx.screen else 1.0
        
        super().__init__(ctx, program_name=shader_name, shader_cache=shader_cache)

    def _compute_autocrop_bbox(self, img):
        data = np.array(img)
        if len(data.shape) == 3 and data.shape[2] == 4:
            alpha = data[:, :, 3]
        else:
            return None
        
        rows = np.any(alpha > 0, axis=1)
        cols = np.any(alpha > 0, axis=0)
        
        if not np.any(rows) or not np.any(cols):
            return None
        
        top = np.argmax(rows)
        bottom = len(rows) - np.argmax(rows[::-1])
        left = np.argmax(cols)
        right = len(cols) - np.argmax(cols[::-1])
        
        return (left, top, right, bottom)

    def get_vertex_data_format(self):
        return [
            ('3f', 'in_position'),
            ('2f', 'in_uv'),
        ]

    def get_vbo(self):
        aspect = self._width / self._height if self._height > 0 else 1.0
        
        left = -aspect * 0.5
        right = aspect * 0.5
        top = 0.5
        bottom = -0.5
        
        u0 = self._offset_x / self._original_width if self._original_width > 0 else 0.0
        v0 = (self._offset_y + self._height) / self._original_height if self._original_height > 0 else 1.0
        u1 = (self._offset_x + self._width) / self._original_width if self._original_width > 0 else 1.0
        v1 = self._offset_y / self._original_height if self._original_height > 0 else 0.0
        
        vertices = np.array([
            left, bottom, 0.0,  u0, v1,
            right, bottom, 0.0, u1, v1,
            right, top, 0.0,    u1, v0,
            left, bottom, 0.0,  u0, v1,
            right, top, 0.0,    u1, v0,
            left, top, 0.0,     u0, v0,
        ], dtype='f4')
        
        return self.ctx.buffer(vertices)


    def update(self, dt):
        pass

    def set_uniforms(self, camera, lights=None, object_color=None, render_settings=None,
                     viewport=None, dir_light_vp=None, receives_shadows=True,
                     highlight_strength=0.0, highlight_color=None):
        model = self.transform.model_matrix()
        
        if self.billboard and camera:
            cam_pos = glm.vec3(camera.position)
            cam_target = cam_pos + glm.vec3(camera.front)
            look_dir = glm.normalize(cam_target - self.transform.position)
            
            yaw = glm.degrees(glm.atan(look_dir.x, look_dir.z))
            rot_quat = glm.quat(glm.radians(glm.vec3(0, yaw, 0)))
            
            model = glm.mat4(1.0)
            model = glm.translate(model, self.transform.position)
            model = model * glm.mat4_cast(rot_quat)
            model = glm.scale(model, self.transform.scale)
        
        view = camera.view_matrix()
        proj = camera.projection_matrix(self._aspect_ratio)
        
        self._set_uniform('u_model', model)
        self._set_uniform('u_view', view)
        self._set_uniform('u_projection', proj)
        
        if self._texture:
            self._texture.use(location=0)
            self._set_uniform('u_texture', 0)
        
        alpha = getattr(self, 'alpha', 1.0)
        self._set_uniform('u_alpha', alpha)

    def destroy(self):
        # Do not release the texture here, as it is managed by the global _SPRITE_CACHE
        self._texture = None
        super().destroy()
