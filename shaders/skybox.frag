#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D u_sky_texture;
uniform vec3 u_cam_forward;
uniform vec3 u_cam_right;
uniform vec3 u_cam_up;
uniform float u_half_tan_fov;
uniform float u_aspect;

void main() {
    // Reconstruct view ray from screen UV and camera vectors
    vec2 ndc = v_uv * 2.0 - 1.0;
    vec3 dir = normalize(u_cam_forward
                       + u_cam_right   * ndc.x * u_half_tan_fov * u_aspect
                       + u_cam_up      * ndc.y * u_half_tan_fov);

    // Map direction to equirectangular UV
    float u = atan(dir.z, dir.x) / (2.0 * 3.14159265) + 0.5;
    float v = asin(clamp(dir.y, -1.0, 1.0)) / 3.14159265 + 0.5;

    frag_color = texture(u_sky_texture, vec2(u, v));
}
