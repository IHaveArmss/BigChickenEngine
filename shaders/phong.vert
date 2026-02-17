#version 330 core

in vec3 in_position;
in vec3 in_normal;
in vec2 in_texcoord;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;

out vec3 v_frag_pos;
out vec3 v_normal;
out vec2 v_texcoord;

void main() {
    vec4 world_pos = u_model * vec4(in_position, 1.0);
    v_frag_pos = world_pos.xyz;

    // Normal matrix = transpose(inverse(model)) — handles non-uniform scale
    v_normal = mat3(transpose(inverse(u_model))) * in_normal;

    v_texcoord = in_texcoord;

    gl_Position = u_projection * u_view * world_pos;
}
