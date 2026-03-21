"""Raycasting utilities — screen-to-floor and object picking."""

import math
import glm


def screen_to_floor(camera, win_size, screen_x, screen_y):
    """Raycast from screen pixel to Y=0 floor plane. Returns glm.vec3 or None."""
    w, h = win_size
    aspect = w / h

    ndc_x = (2.0 * screen_x / w) - 1.0
    ndc_y = 1.0 - (2.0 * screen_y / h)

    proj = camera.projection_matrix(aspect)
    view = camera.view_matrix()
    inv_proj = glm.inverse(proj)
    inv_view = glm.inverse(view)

    ray_clip = glm.vec4(ndc_x, ndc_y, -1.0, 1.0)
    ray_eye = inv_proj * ray_clip
    ray_eye = glm.vec4(ray_eye.x, ray_eye.y, -1.0, 0.0)

    ray_world = glm.vec3(inv_view * ray_eye)
    ray_dir = glm.normalize(ray_world)
    ray_origin = glm.vec3(camera.position)

    if abs(ray_dir.y) < 1e-6:
        return None
    t = -ray_origin.y / ray_dir.y
    if t < 0:
        return None
    return ray_origin + ray_dir * t


def _ray_sphere_test(ray_origin, ray_dir, center, radius):
    """Returns distance t along ray to sphere, or None if no hit."""
    oc = ray_origin - center
    a = glm.dot(ray_dir, ray_dir)
    b = 2.0 * glm.dot(oc, ray_dir)
    c = glm.dot(oc, oc) - radius * radius
    disc = b * b - 4.0 * a * c
    if disc < 0:
        return None
    sqrt_disc = math.sqrt(disc)
    t1 = (-b - sqrt_disc) / (2.0 * a)
    t2 = (-b + sqrt_disc) / (2.0 * a)
    t = t1 if t1 > 0 else t2
    return t if t > 0 else None


def pick_object(camera, scene_objects):
    """Pick an object using a ray from camera center. Returns index or -1."""
    ray_origin = glm.vec3(camera.position)
    ray_dir = glm.normalize(glm.vec3(camera.front))
    return _pick_from_ray(ray_origin, ray_dir, scene_objects)


def pick_object_from_screen(camera, win_size, scene_objects, screen_x, screen_y):
    """Pick an object via screen-space ray (for cursor mode). Returns index or -1."""
    w, h = win_size
    aspect = w / h
    ndc_x = (2.0 * screen_x / w) - 1.0
    ndc_y = 1.0 - (2.0 * screen_y / h)

    proj = camera.projection_matrix(aspect)
    view = camera.view_matrix()
    inv_proj = glm.inverse(proj)
    inv_view = glm.inverse(view)

    ray_clip = glm.vec4(ndc_x, ndc_y, -1.0, 1.0)
    ray_eye = inv_proj * ray_clip
    ray_eye = glm.vec4(ray_eye.x, ray_eye.y, -1.0, 0.0)
    ray_world = glm.vec3(inv_view * ray_eye)
    ray_dir = glm.normalize(ray_world)
    ray_origin = glm.vec3(camera.position)

    return _pick_from_ray(ray_origin, ray_dir, scene_objects)


def _pick_from_ray(ray_origin, ray_dir, scene_objects):
    """Internal: find closest object hit by ray. Returns index or -1."""
    best_t = float('inf')
    best_idx = -1
    for i, obj in enumerate(scene_objects):
        center = glm.vec3(obj.position)
        scl = obj.scale
        radius = max(max(scl.x, scl.y, scl.z) * 50.0, 5.0)
        t = _ray_sphere_test(ray_origin, ray_dir, center, radius)
        if t is not None and t < best_t:
            best_t = t
            best_idx = i
    return best_idx
