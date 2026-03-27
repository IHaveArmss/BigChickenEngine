#version 330 core

in vec3 in_position;
in vec4 in_joints;
in vec4 in_weights;

#define MAX_BONES 128
uniform bool u_has_skin;
uniform mat4 u_bone_matrices[MAX_BONES];

uniform mat4 u_model;
uniform mat4 u_light_vp;

void main() {
    vec4 local_pos = vec4(in_position, 1.0);
    if (u_has_skin) {
        ivec4 j = ivec4(in_joints);
        float w_sum = in_weights.x + in_weights.y + in_weights.z + in_weights.w;
        vec4 w = (w_sum > 1e-6) ? in_weights / w_sum : vec4(1.0, 0.0, 0.0, 0.0);
        mat4 skin_mat = w.x * u_bone_matrices[j.x]
                      + w.y * u_bone_matrices[j.y]
                      + w.z * u_bone_matrices[j.z]
                      + w.w * u_bone_matrices[j.w];
        local_pos = skin_mat * local_pos;
    }
    gl_Position = u_light_vp * u_model * local_pos;
}
