"""Renderer — collects lights, frustum-culls, and draws the scene."""

import glm
import math
import moderngl
import os
from core.model_mesh import ModelMesh


def _extract_frustum_planes(vp):
    """Extract 6 frustum planes (left, right, bottom, top, near, far) from a
    view-projection matrix.  Each plane is (a, b, c, d) normalised so that
    a*x + b*y + c*z + d >= 0 means the point is inside (or on) the plane."""
    raw = [
        (vp[0][3] + vp[0][0], vp[1][3] + vp[1][0], vp[2][3] + vp[2][0], vp[3][3] + vp[3][0]),
        (vp[0][3] - vp[0][0], vp[1][3] - vp[1][0], vp[2][3] - vp[2][0], vp[3][3] - vp[3][0]),
        (vp[0][3] + vp[0][1], vp[1][3] + vp[1][1], vp[2][3] + vp[2][1], vp[3][3] + vp[3][1]),
        (vp[0][3] - vp[0][1], vp[1][3] - vp[1][1], vp[2][3] - vp[2][1], vp[3][3] - vp[3][1]),
        (vp[0][3] + vp[0][2], vp[1][3] + vp[1][2], vp[2][3] + vp[2][2], vp[3][3] + vp[3][2]),
        (vp[0][3] - vp[0][2], vp[1][3] - vp[1][2], vp[2][3] - vp[2][2], vp[3][3] - vp[3][2]),
    ]
    planes = []
    for a, b, c, d in raw:
        length = math.sqrt(a * a + b * b + c * c)
        if length > 1e-8:
            inv = 1.0 / length
            planes.append((a * inv, b * inv, c * inv, d * inv))
        else:
            planes.append((a, b, c, d))
    return planes


def _sphere_in_frustum(planes, center, radius):
    """Return False if the bounding sphere is fully outside any frustum plane."""
    cx, cy, cz = center.x, center.y, center.z
    for a, b, c, d in planes:
        if a * cx + b * cy + c * cz + d < -radius:
            return False
    return True


class Renderer:
    """Handles clearing, light collection, frustum-culls, and object rendering,
    and wireframe highlights."""

    def __init__(self, ctx):
        self.ctx = ctx
        self._pp_program = None
        self._pp_vao = None
        self._scene_tex = None
        self._shadow_vao_cache = {}
        self._depth_rb = None
        self._scene_fbo = None
        self._fbo_size = (0, 0)
        self._dir_shadow_program = None
        self._dir_shadow_tex = None
        self._dir_shadow_fbo = None
        self._dir_shadow_res = 0
        self._dir_light_vp = glm.mat4(1.0)

        # Multi-point-shadow system: up to MAX_POINT_SHADOWS lights
        self._point_shadow_program = None
        self._point_shadow_texs = [None] * 4
        self._point_shadow_fbos = [None] * 4
        self._point_shadow_res = 0
        self._point_shadow_vps = [glm.mat4(1.0)] * 4
        self._point_shadow_count = 0
        # Maps light index (in the lights[] array) → shadow slot (0..3), or -1
        self._light_shadow_slots = [-1] * 8

        self._init_postprocess()
        self._init_shadow_programs()

    def _init_postprocess(self):
        shader_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shaders')
        with open(os.path.join(shader_dir, 'screen.vert'), 'r') as f:
            vs = f.read()
        with open(os.path.join(shader_dir, 'postprocess.frag'), 'r') as f:
            fs = f.read()
        self._pp_program = self.ctx.program(vertex_shader=vs, fragment_shader=fs)
        self._pp_vao = self.ctx.vertex_array(self._pp_program, [])

    def _init_shadow_programs(self):
        shader_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shaders')
        with open(os.path.join(shader_dir, 'shadow_depth.vert'), 'r') as f:
            vs = f.read()
        with open(os.path.join(shader_dir, 'shadow_depth.frag'), 'r') as f:
            fs = f.read()
        self._dir_shadow_program = self.ctx.program(vertex_shader=vs, fragment_shader=fs)
        self._point_shadow_program = self._dir_shadow_program

    def _ensure_directional_shadow_resources(self, resolution):
        res = int(max(256, resolution))
        if res == self._dir_shadow_res and self._dir_shadow_tex is not None and self._dir_shadow_fbo is not None:
            return
        if self._dir_shadow_fbo is not None:
            self._dir_shadow_fbo.release()
            self._dir_shadow_fbo = None
        if self._dir_shadow_tex is not None:
            self._dir_shadow_tex.release()
            self._dir_shadow_tex = None
        self._dir_shadow_tex = self.ctx.depth_texture((res, res))
        self._dir_shadow_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self._dir_shadow_tex.repeat_x = False
        self._dir_shadow_tex.repeat_y = False
        self._dir_shadow_fbo = self.ctx.framebuffer(depth_attachment=self._dir_shadow_tex)
        self._dir_shadow_res = res

    def _ensure_point_shadow_resources(self, resolution, count):
        """Ensure we have count point shadow depth textures at resolution."""
        res = int(max(256, resolution))
        if res == self._point_shadow_res and all(
            self._point_shadow_texs[i] is not None for i in range(count)
        ):
            return
        for i in range(4):
            if self._point_shadow_fbos[i] is not None:
                self._point_shadow_fbos[i].release()
                self._point_shadow_fbos[i] = None
            if self._point_shadow_texs[i] is not None:
                self._point_shadow_texs[i].release()
                self._point_shadow_texs[i] = None
        for i in range(count):
            tex = self.ctx.depth_texture((res, res))
            tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
            tex.repeat_x = False
            tex.repeat_y = False
            self._point_shadow_texs[i] = tex
            self._point_shadow_fbos[i] = self.ctx.framebuffer(depth_attachment=tex)
        self._point_shadow_res = res

    def _build_light_vp_directional(self, camera, main_light_dir, shadow_distance):
        dir_n = glm.normalize(glm.vec3(main_light_dir))
        cam_pos = glm.vec3(camera.position)
        # Snap the shadow centre to a fine grid aligned to shadow-map texels
        # to prevent sub-pixel swimming / shimmer as the camera moves.
        r = float(shadow_distance)
        texel_world = (2.0 * r) / float(self._dir_shadow_res) if self._dir_shadow_res > 0 else 1.0
        cell = max(texel_world, 1.0)
        center = glm.vec3(
            glm.floor(cam_pos.x / cell) * cell,
            0.0,  # keep shadow centre at ground level for better coverage
            glm.floor(cam_pos.z / cell) * cell,
        )
        eye = center - dir_n * r * 1.5
        up = glm.vec3(0.0, 1.0, 0.0)
        if abs(glm.dot(up, dir_n)) > 0.98:
            up = glm.vec3(0.0, 0.0, 1.0)
        view = glm.lookAt(eye, center, up)
        proj = glm.ortho(-r, r, -r, r, 0.5, r * 4.0)
        return proj * view

    def _build_point_light_vp(self, light_pos):
        """Build a VP matrix for a point light looking downward."""
        pos = glm.vec3(light_pos)
        target = pos + glm.vec3(0.0, -1.0, 0.0)
        up = glm.vec3(0.0, 0.0, 1.0)
        view = glm.lookAt(pos, target, up)
        proj = glm.perspective(glm.radians(120.0), 1.0, 0.1, 60.0)
        return proj * view

    def _render_shadow_meshes(self, renderables, shadow_program, light_vp):
        shadow_program['u_light_vp'].write(light_vp.to_bytes())
        program_id = id(shadow_program)
        for obj in renderables:
            if getattr(obj, 'alpha', 1.0) < 1.0:
                continue
            model = obj.transform.model_matrix()
            if 'u_model' in shadow_program:
                shadow_program['u_model'].write(model.to_bytes())

            has_skin = isinstance(obj, ModelMesh) and getattr(obj, '_has_skin', False) and getattr(obj, 'animator', None) is not None
            if 'u_has_skin' in shadow_program:
                shadow_program['u_has_skin'].value = bool(has_skin)
            if has_skin and 'u_bone_matrices' in shadow_program:
                shadow_program['u_bone_matrices'].write(bytes(obj.animator.bone_bytes))

            cache_key = (id(obj), program_id, has_skin)
            if cache_key not in self._shadow_vao_cache:
                layout = obj.get_vertex_data_format()
                parts = []
                attrs = []
                for fmt, name in layout:
                    if name in shadow_program:
                        parts.append(fmt)
                        attrs.append(name)
                    else:
                        count = int(fmt.replace('f', ''))
                        parts.append(f'{count * 4}x')
                combined_fmt = ' '.join(parts)
                if hasattr(obj, '_index_buffer') and getattr(obj, '_index_buffer') is not None:
                    vao = self.ctx.vertex_array(shadow_program, [(obj.vbo, combined_fmt, *attrs)], obj._index_buffer)
                else:
                    vao = self.ctx.vertex_array(shadow_program, [(obj.vbo, combined_fmt, *attrs)])
                self._shadow_vao_cache[cache_key] = vao
            else:
                vao = self._shadow_vao_cache[cache_key]
            vao.render()

    def resize(self, w, h):
        w = int(w)
        h = int(h)
        if w <= 0 or h <= 0:
            return
        if (w, h) == self._fbo_size:
            return

        # Release old
        if self._scene_fbo is not None:
            self._scene_fbo.release()
            self._scene_fbo = None
        if self._scene_tex is not None:
            self._scene_tex.release()
            self._scene_tex = None
        if self._depth_rb is not None:
            self._depth_rb.release()
            self._depth_rb = None

        # Recreate
        self._scene_tex = self.ctx.texture((w, h), 4)
        self._scene_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self._scene_tex.repeat_x = False
        self._scene_tex.repeat_y = False

        self._depth_rb = self.ctx.depth_renderbuffer((w, h))
        self._scene_fbo = self.ctx.framebuffer(color_attachments=[self._scene_tex], depth_attachment=self._depth_rb)
        self._fbo_size = (w, h)

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
               dev_mode_active, selected_index,
               render_settings=None, win_size=None,
               main_light_dir=None, main_light_color=None):
        """Full frame render with frustum culling + optional postprocess."""
        if win_size:
            self.resize(win_size[0], win_size[1])

        ps2_enabled = bool(getattr(render_settings, "ps2_enabled", False))
        use_pp = bool(ps2_enabled and getattr(render_settings, "postprocess_enabled", False))

        target = self._scene_fbo if use_pp and self._scene_fbo is not None else self.ctx.screen
        target.use()
        self.ctx.clear(0.08, 0.08, 0.12)

        rs = render_settings
        dir_shadows = bool(getattr(rs, 'directional_shadows_enabled', False))
        if dir_shadows:
            self._ensure_directional_shadow_resources(int(getattr(rs, 'directional_shadow_resolution', 1024)))
            self._dir_light_vp = self._build_light_vp_directional(
                camera,
                main_light_dir if main_light_dir is not None else glm.vec3(-0.5, -1.0, -0.3),
                float(getattr(rs, 'directional_shadow_distance', 40.0)),
            )
            self._dir_shadow_fbo.use()
            self.ctx.clear(depth=1.0)
            self.ctx.disable(moderngl.BLEND)
            self.ctx.enable(moderngl.DEPTH_TEST)
            casters = [r for r in all_renderables if getattr(getattr(r, 'owner_obj', None), 'casts_shadows', True)]
            self._render_shadow_meshes(casters, self._dir_shadow_program, self._dir_light_vp)
            target.use()
            self.ctx.clear(0.08, 0.08, 0.12)

        # ── Multi-point-light shadows ──
        self._light_shadow_slots = [-1] * 8
        self._point_shadow_count = 0
        max_point = int(getattr(rs, 'max_shadowed_spot_lights', 4))
        if bool(getattr(rs, 'spot_shadows_enabled', False)) and max_point > 0:
            # Collect shadow-casting lights (skip sun = index 0 in the lights array)
            shadow_lights = []  # list of (light_array_index, scene_object)
            light_idx = 1  # sun is always index 0
            for so in scene_objects:
                if so.is_light and bool(getattr(so, 'light_casts_shadows', False)):
                    if light_idx < 8 and len(shadow_lights) < min(max_point, 4):
                        shadow_lights.append((light_idx, so))
                light_idx += 1

            if shadow_lights:
                self._ensure_point_shadow_resources(
                    int(getattr(rs, 'spot_shadow_resolution', 512)),
                    len(shadow_lights),
                )
                casters = [r for r in all_renderables
                           if getattr(getattr(r, 'owner_obj', None), 'casts_shadows', True)]
                for slot, (li, so) in enumerate(shadow_lights):
                    vp = self._build_point_light_vp(so.position)
                    self._point_shadow_vps[slot] = vp
                    self._light_shadow_slots[li] = slot

                    self._point_shadow_fbos[slot].use()
                    self.ctx.clear(depth=1.0)
                    self.ctx.disable(moderngl.BLEND)
                    self.ctx.enable(moderngl.DEPTH_TEST)
                    self._render_shadow_meshes(casters, self._point_shadow_program, vp)

                self._point_shadow_count = len(shadow_lights)
                target.use()
                self.ctx.clear(0.08, 0.08, 0.12)

        if main_light_dir is not None:
            sun_pos = glm.vec3(camera.position) - glm.normalize(glm.vec3(main_light_dir)) * 120.0
            lights = self.collect_lights(
                scene_objects,
                sun_pos,
                main_light_color if main_light_color is not None else orbiting_light_color,
            )
        else:
            lights = self.collect_lights(scene_objects, orbiting_light_pos, orbiting_light_color)

        aspect = self.ctx.screen.width / self.ctx.screen.height
        vp = camera.projection_matrix(aspect) * camera.view_matrix()
        frustum = _extract_frustum_planes(vp)

        opaque = []
        transparent = []
        for obj in all_renderables:
            pos = getattr(obj.transform, 'position', glm.vec3(0))
            # Prefer an explicit bounding_radius if set (e.g. large flat floor);
            # otherwise fall back to the transform scale approximation.
            if hasattr(obj, 'bounding_radius'):
                radius = obj.bounding_radius
            else:
                scl = getattr(obj.transform, 'scale', glm.vec3(1))
                radius = max(abs(scl.x), abs(scl.y), abs(scl.z)) * 0.866
            if not _sphere_in_frustum(frustum, pos, radius):
                continue

            if getattr(obj, 'alpha', 1.0) < 1.0:
                transparent.append(obj)
            elif hasattr(obj, 'meshes') and obj.meshes and getattr(obj.meshes[0], '_shader_name', None) == 'textured':
                transparent.append(obj)
            else:
                opaque.append(obj)

        viewport = (int(self.ctx.screen.width), int(self.ctx.screen.height))
        if dir_shadows and self._dir_shadow_tex is not None:
            self._dir_shadow_tex.use(location=4)
        # Bind point shadow textures at locations 5..8
        for i in range(self._point_shadow_count):
            if self._point_shadow_texs[i] is not None:
                self._point_shadow_texs[i].use(location=5 + i)

        for obj in opaque:
            owner = getattr(obj, 'owner_obj', None)
            hl = 0.35 if getattr(owner, 'is_hovered', False) else 0.0
            obj.set_uniforms(
                camera,
                lights=lights,
                render_settings=render_settings,
                viewport=viewport,
                dir_light_vp=self._dir_light_vp if dir_shadows else None,
                receives_shadows=bool(getattr(owner, 'receives_shadows', True)),
                highlight_strength=hl,
            )
            if hasattr(obj, '_set_uniform'):
                obj._set_uniform('u_dir_shadow_map', 4)
                obj._set_uniform('u_directional_shadows_enabled', bool(dir_shadows))
                # Point shadow uniforms
                obj._set_uniform('u_num_point_shadows', self._point_shadow_count)
                for si in range(4):
                    obj._set_uniform(f'u_point_shadow_{si}', 5 + si)
                    obj._set_uniform(f'u_point_shadow_vps[{si}]', self._point_shadow_vps[si])
                if 'u_light_shadow_slot' in obj.program:
                    obj.program['u_light_shadow_slot'].value = tuple(self._light_shadow_slots)
            obj.render()

        if transparent:
            cam_pos = camera.position
            transparent.sort(
                key=lambda o: glm.distance2(o.transform.position, cam_pos),
                reverse=True,
            )
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
            for obj in transparent:
                owner = getattr(obj, 'owner_obj', None)
                hl = 0.35 if getattr(owner, 'is_hovered', False) else 0.0
                obj.set_uniforms(
                    camera,
                    lights=lights,
                    render_settings=render_settings,
                    viewport=viewport,
                    dir_light_vp=self._dir_light_vp if dir_shadows else None,
                    receives_shadows=bool(getattr(owner, 'receives_shadows', True)),
                    highlight_strength=hl,
                )
                if hasattr(obj, '_set_uniform'):
                    obj._set_uniform('u_dir_shadow_map', 4)
                    obj._set_uniform('u_directional_shadows_enabled', bool(dir_shadows))
                    obj._set_uniform('u_num_point_shadows', self._point_shadow_count)
                    for si in range(4):
                        obj._set_uniform(f'u_point_shadow_{si}', 5 + si)
                        obj._set_uniform(f'u_point_shadow_vps[{si}]', self._point_shadow_vps[si])
                    if 'u_light_shadow_slot' in obj.program:
                        obj.program['u_light_shadow_slot'].value = tuple(self._light_shadow_slots)
                obj.render()
            self.ctx.disable(moderngl.BLEND)

        if dev_mode_active and 0 <= selected_index < len(scene_objects):
            sel = scene_objects[selected_index]
            self.ctx.wireframe = True
            for mesh in sel.meshes:
                # ModelMesh instances own their material colours and textures.
                # Use the highlight system (additive tint over the texture) instead
                # of object_color so the texture is preserved while still showing
                # a clear green selection indicator on the wireframe edges.
                if isinstance(mesh, ModelMesh):
                    mesh.set_uniforms(
                        camera, lights=lights,
                        render_settings=render_settings,
                        viewport=viewport,
                        dir_light_vp=self._dir_light_vp if dir_shadows else None,
                        receives_shadows=True,
                        highlight_strength=0.6,
                        highlight_color=glm.vec3(0.0, 0.9, 0.35),
                    )
                else:
                    mesh.set_uniforms(
                        camera, lights=lights,
                        object_color=glm.vec3(0.0, 1.0, 0.4),
                        render_settings=render_settings,
                        viewport=viewport,
                        dir_light_vp=self._dir_light_vp if dir_shadows else None,
                        receives_shadows=True,
                    )
                mesh.render()
            self.ctx.wireframe = False

        # Postprocess to screen
        if use_pp and self._scene_tex is not None:
            self.ctx.screen.use()
            self.ctx.disable(moderngl.DEPTH_TEST)
            self._scene_tex.use(location=0)
            if 'u_scene' in self._pp_program:
                self._pp_program['u_scene'].value = 0
            if 'u_resolution' in self._pp_program:
                self._pp_program['u_resolution'].value = (float(self._fbo_size[0]), float(self._fbo_size[1]))

            # Settings (all toggleable)
            rs = render_settings
            def _u(name, value):
                if name in self._pp_program:
                    self._pp_program[name].value = value

            _u('u_ps2_enabled', ps2_enabled)
            _u('u_pixel_size', int(max(1, getattr(rs, "pixel_size", 3))))
            _u('u_quantize_enabled', bool(getattr(rs, "quantize_enabled", True)))
            _u('u_quantize_steps', int(max(2, getattr(rs, "quantize_steps", 32))))
            _u('u_dither_enabled', bool(getattr(rs, "dither_enabled", False)))

            self._pp_vao.render(moderngl.TRIANGLE_STRIP, vertices=4)
            self.ctx.enable(moderngl.DEPTH_TEST)

        hud.render()

