#version 330 core

in vec3 v_frag_pos;
in vec3 v_normal;
in vec2 v_texcoord;

uniform vec3 u_light_pos;
uniform vec3 u_light_color;
uniform vec3 u_object_color;
uniform vec3 u_view_pos;       // camera position for specular

out vec4 frag_color;

void main() {
    // --- Ambient ---
    float ambient_strength = 0.15;
    vec3 ambient = ambient_strength * u_light_color;

    // --- Diffuse ---
    vec3 norm = normalize(v_normal);
    vec3 light_dir = normalize(u_light_pos - v_frag_pos);
    float diff = max(dot(norm, light_dir), 0.0);
    vec3 diffuse = diff * u_light_color;

    // --- Specular (Blinn-Phong) ---
    float specular_strength = 0.5;
    vec3 view_dir = normalize(u_view_pos - v_frag_pos);
    vec3 halfway = normalize(light_dir + view_dir);
    float spec = pow(max(dot(norm, halfway), 0.0), 32.0);
    vec3 specular = specular_strength * spec * u_light_color;

    vec3 result = (ambient + diffuse + specular) * u_object_color;

    // Dummy use of v_texcoord to prevent the compiler from optimizing out in_texcoord
    // This will be replaced with actual texture sampling in Phase 3
    result += v_texcoord.x * 0.0;

    frag_color = vec4(result, 1.0);
}
