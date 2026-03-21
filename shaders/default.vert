#version 330 core

in vec3 in_position;
uniform float u_time; // Pass time or angle from Python
out vec3 v_color;

void main() {
    float angle = u_time;

    mat3 rot = mat3(
        cos(angle), -sin(angle), 0.0,
        sin(angle),  cos(angle), 0.0,
        0.0,         0.0,        1.0
    );

    vec3 pos = rot * in_position;

    gl_Position = vec4(pos, 1.0);
    v_color = vec3(0.49, 0.48, 1.0);
}