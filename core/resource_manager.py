import os
import json
import moderngl
from core.model_loader import load_gltf, load_obj


class ResourceManager:
    """
    Centralized cache for all assets (Models, Textures, Sprites).
    Prevents redundant disk reads and speeds up scene transitions.
    """

    def __init__(self, ctx, texture_loader):
        self.ctx = ctx
        self.texture_loader = texture_loader
        
        self.model_cache = {}   # path -> list of MeshData dicts
        self.sprite_cache = {}  # (path, autocrop) -> {texture, width, height, etc.}

    def get_model_data(self, path, fmt='glb'):
        """Load and cache GLTF/OBJ data as a list of dictionaries."""
        abs_path = os.path.abspath(path)
        if abs_path in self.model_cache:
            return self.model_cache[abs_path]

        if not os.path.exists(abs_path):
            print(f"[ResourceManager] WARNING: model not found: {abs_path}")
            return []

        print(f"[ResourceManager] Loading and caching: {path}")
        if fmt in ('glb', 'gltf'):
            data = load_gltf(abs_path)
        else:
            data = load_obj(abs_path)

        self.model_cache[abs_path] = data
        return data

    def pre_load_scenes(self, scene_files):
        """
        Scan a list of scene JSON files and pre-load every unique asset.
        Call this at engine startup to avoid stutters.
        """
        print(f"[ResourceManager] Pre-loading assets from {len(scene_files)} scenes...")
        unique_models = set()
        unique_sprites = set()

        for scene_path in scene_files:
            if not os.path.exists(scene_path):
                continue
                
            try:
                with open(scene_path, 'r') as f:
                    data = json.load(f)
                
                for obj in data.get('objects', []):
                    fmt = obj.get('format', 'obj')
                    model = obj.get('model')
                    if model and fmt not in ('cube', 'triangle', 'light', 'sprite'):
                        unique_models.add((model, fmt))
                    
                    sprite = obj.get('sprite_path')
                    if sprite and fmt == 'sprite':
                        autocrop = obj.get('autocrop', True)
                        unique_sprites.add((sprite, autocrop))
            except Exception as e:
                print(f"[ResourceManager] ERROR scanning {scene_path}: {e}")

        # Bulk Load
        for model_path, fmt in unique_models:
            self.get_model_data(model_path, fmt)
            
        # Textures are handled by the TextureLoader (already has a cache)
        # Sprites will be handled as needed by SpriteMesh (transparent caching)
        print(f"[ResourceManager] Pre-load complete. {len(unique_models)} models cached.")

    def clear(self):
        """Clear CPU-side caches."""
        self.model_cache.clear()
        self.sprite_cache.clear()
