#version 330 core

in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;
in vec4 in_joints;
in vec4 in_weights;

#define MAX_BONES 128

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
uniform mat4 u_bone_matrices[MAX_BONES];
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
    ivec4 j = ivec4(in_joints);

    // Normalise weights so they always sum to 1.0.
    // This also handles unweighted vertices (all-zero weights) by falling
    // back to the root bone, avoiding gl_Position = (0,0,0,0) → screen centre.
    float w_sum = in_weights.x + in_weights.y + in_weights.z + in_weights.w;
    vec4 w = (w_sum > 1e-6) ? in_weights / w_sum : vec4(1.0, 0.0, 0.0, 0.0);

    mat4 skin_mat = w.x * u_bone_matrices[j.x]
                  + w.y * u_bone_matrices[j.y]
                  + w.z * u_bone_matrices[j.z]
                  + w.w * u_bone_matrices[j.w];

    vec4 skinned_pos = skin_mat * vec4(in_position, 1.0);
    vec3 skinned_normal = mat3(skin_mat) * in_normal;

    vec4 world_pos = u_model * skinned_pos;
    v_frag_pos = world_pos.xyz;
    v_normal = u_normal_matrix * skinned_normal;
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
