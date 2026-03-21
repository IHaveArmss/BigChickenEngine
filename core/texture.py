import os
from PIL import Image


class TextureLoader:
    """Load images as moderngl textures with caching."""

    def __init__(self, ctx):
        self.ctx = ctx
        self._cache = {}  # path -> moderngl.Texture

    def load(self, path):
        """Load a texture from an image file. Returns a moderngl.Texture."""
        abs_path = os.path.abspath(path)
        if abs_path in self._cache:
            return self._cache[abs_path]

        img = Image.open(abs_path).convert('RGBA')
        img = img.transpose(Image.FLIP_TOP_BOTTOM)  # OpenGL expects bottom-left origin

        texture = self.ctx.texture(img.size, 4, img.tobytes())
        texture.filter = (self.ctx.LINEAR_MIPMAP_LINEAR, self.ctx.LINEAR)
        texture.build_mipmaps()
        texture.anisotropy = 16.0

        self._cache[abs_path] = texture
        return texture

    def load_from_bytes(self, data, width, height, components=4, name=None, flip=False):
        """Load a texture from raw bytes (used by glTF loader).
        flip=False for glTF (images are already in correct orientation for OpenGL UV space)."""
        if name and name in self._cache:
            return self._cache[name]

        texture = self.ctx.texture((width, height), components, data)
        texture.filter = (self.ctx.LINEAR_MIPMAP_LINEAR, self.ctx.LINEAR)
        texture.build_mipmaps()
        texture.anisotropy = 16.0

        if name:
            self._cache[name] = texture
        return texture

    def destroy(self):
        for tex in self._cache.values():
            tex.release()
        self._cache.clear()
