#version 330 core

in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
uniform mat3 u_normal_matrix;

uniform bool u_ps2_enabled;
uniform bool u_wobble_enabled;
uniform int u_wobble_pixel_size;
uniform vec2 u_viewport;
uniform mat4 u_dir_light_vp;

out vec3 v_frag_pos;
out vec3 v_normal;
out vec2 v_texcoord;
out vec4 v_dir_light_space_pos;

void main() {
    vec4 world_pos = u_model * vec4(in_position, 1.0);
    v_frag_pos = world_pos.xyz;

    v_normal = u_normal_matrix * in_normal;

    v_texcoord = in_texcoord;
    v_dir_light_space_pos = u_dir_light_vp * world_pos;

    vec4 clip = u_projection * u_view * world_pos;
    if (u_ps2_enabled && u_wobble_enabled && u_viewport.x > 0.0 && u_viewport.y > 0.0) {
        float px = float(max(u_wobble_pixel_size, 1));
        vec2 ndc = clip.xy / clip.w;
        vec2 screen = (ndc * 0.5 + 0.5) * u_viewport;
        screen = floor(screen / px) * px;
        ndc = (screen / u_viewport) * 2.0 - 1.0;
        clip.xy = ndc * clip.w;
    }
    gl_Position = clip;
}
