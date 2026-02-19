"""Renderer — collects lights and draws the scene."""

from pyglm import glm
import moderngl


class Renderer:
    """Handles clearing, light collection, object rendering, and wireframe highlights."""

    def __init__(self, ctx):
        self.ctx = ctx

    def collect_lights(self, scene_objects, orbiting_light_pos, orbiting_light_color):
        """Gather all lights into a list of (position, color) tuples."""
        lights = [(orbiting_light_pos, orbiting_light_color)]
        for obj in scene_objects:
            if obj.is_light:
                lights.append((
                    glm.vec3(obj.position),
                    obj.light_color * obj.light_intensity
                ))
        return lights

    def render(self, all_renderables, scene_objects, camera, hud,
               orbiting_light_pos, orbiting_light_color,
               dev_mode_active, selected_index):
        """Full frame render."""
        self.ctx.clear(0.08, 0.08, 0.12)

        lights = self.collect_lights(scene_objects, orbiting_light_pos, orbiting_light_color)

        # Separate opaque and transparent objects
        opaque = []
        transparent = []
        for obj in all_renderables:
            if getattr(obj, 'alpha', 1.0) < 1.0:
                transparent.append(obj)
            else:
                opaque.append(obj)

        # Render opaque first
        for obj in opaque:
            obj.set_uniforms(camera, lights=lights)
            obj.render()

        # Render transparent with blending
        if transparent:
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
            for obj in transparent:
                obj.set_uniforms(camera, lights=lights)
                obj.render()
            self.ctx.disable(moderngl.BLEND)

        # Wireframe highlight for selected object
        if dev_mode_active and 0 <= selected_index < len(scene_objects):
            sel = scene_objects[selected_index]
            self.ctx.wireframe = True
            for mesh in sel.meshes:
                mesh.set_uniforms(
                    camera, lights=lights,
                    object_color=glm.vec3(0.0, 1.0, 0.4),
                )
                mesh.render()
            self.ctx.wireframe = False

        hud.render()

