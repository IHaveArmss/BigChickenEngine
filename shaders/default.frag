#version 330 core

in vec3 v_color;
uniform float u_opacity;
out vec4 fragColor;

void main() {
    vec3 dummy = v_color*0.0001;
    fragColor = vec4(vec3(0.49, 0.48, 1.0)+dummy, u_opacity);
}