#version 330 core

uniform vec3 u_object_color;
uniform float u_alpha;

out vec4 frag_color;

void main() {
    frag_color = vec4(u_object_color, u_alpha);
}
