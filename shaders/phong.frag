#version 330 core

in vec3 v_frag_pos;
in vec3 v_normal;
in vec2 v_texcoord;
in vec4 v_dir_light_space_pos;

// Change this number to support more or fewer lights
#define MAX_LIGHTS 8
#define MAX_POINT_SHADOWS 4

uniform int u_num_lights;
uniform vec3 u_light_pos[MAX_LIGHTS];
uniform vec3 u_light_color[MAX_LIGHTS];

uniform vec3 u_object_color;
uniform vec3 u_view_pos;
uniform float u_alpha;

uniform float u_highlight_strength;
uniform vec3  u_highlight_color;

uniform sampler2D u_texture;
uniform bool u_use_texture;

// Retro/PS2 style (optional)
uniform bool u_ps2_enabled;
uniform bool u_lighting_ramp_enabled;
uniform int u_lighting_ramp_steps;
uniform bool u_specular_banding_enabled;
uniform int u_specular_steps;
uniform bool u_directional_shadows_enabled;
uniform bool u_receives_shadows;
uniform float u_shadow_bias;
uniform sampler2D u_dir_shadow_map;
uniform mat4 u_dir_light_vp;
uniform vec3 u_ambient_color;
uniform float u_ambient_strength;

// Per-light shadow mapping: up to MAX_POINT_SHADOWS lights can cast shadows.
// u_light_shadow_slot[i] = -1 means light i has no shadow map,
//                          0..3 means it uses point shadow map at that index.
uniform int u_light_shadow_slot[MAX_LIGHTS];
uniform int u_num_point_shadows;
uniform mat4 u_point_shadow_vps[MAX_POINT_SHADOWS];
uniform sampler2D u_point_shadow_0;
uniform sampler2D u_point_shadow_1;
uniform sampler2D u_point_shadow_2;
uniform sampler2D u_point_shadow_3;

out vec4 frag_color;

float sample_shadow(sampler2D smap, vec4 light_space_pos, float bias) {
    vec3 proj = light_space_pos.xyz / max(light_space_pos.w, 1e-6);
    proj = proj * 0.5 + 0.5;
    if (proj.x < 0.0 || proj.x > 1.0 || proj.y < 0.0 || proj.y > 1.0 || proj.z > 1.0) {
        return 1.0;
    }
    float closest = texture(smap, proj.xy).r;
    float current = proj.z - bias;
    return current > closest ? 0.0 : 1.0;
}

float get_point_shadow(int slot, float bias) {
    vec4 lsp = u_point_shadow_vps[slot] * vec4(v_frag_pos, 1.0);
    if (slot == 0) return sample_shadow(u_point_shadow_0, lsp, bias);
    if (slot == 1) return sample_shadow(u_point_shadow_1, lsp, bias);
    if (slot == 2) return sample_shadow(u_point_shadow_2, lsp, bias);
    return sample_shadow(u_point_shadow_3, lsp, bias);
}

void main() {
    // Base color — from texture or uniform
    vec3 base_color;
    if (u_use_texture) {
        base_color = texture(u_texture, v_texcoord).rgb;
    } else {
        base_color = u_object_color;
    }

    vec3 norm = normalize(v_normal);
    vec3 view_dir = normalize(u_view_pos - v_frag_pos);

    // Ambient/fill is now independent and user-controllable.
    vec3 ambient = u_ambient_strength * u_ambient_color;

    // Accumulate diffuse + specular from all lights
    vec3 total_diffuse = vec3(0.0);
    vec3 total_specular = vec3(0.0);

    for (int i = 0; i < u_num_lights && i < MAX_LIGHTS; i++) {
        vec3 light_dir = normalize(u_light_pos[i] - v_frag_pos);

        // Diffuse
        float diff = max(dot(norm, light_dir), 0.0);

        float light_shadow = 1.0;

        // Directional shadow (sun = light 0) — compute per-pixel to avoid
        // wobble interpolation artifacts
        if (u_receives_shadows && u_directional_shadows_enabled && i == 0) {
            vec4 frag_light_pos = u_dir_light_vp * vec4(v_frag_pos, 1.0);
            light_shadow *= sample_shadow(u_dir_shadow_map, frag_light_pos, u_shadow_bias);
        }

        // Point light shadows (any light with a shadow slot assigned)
        if (u_receives_shadows && u_light_shadow_slot[i] >= 0 && u_light_shadow_slot[i] < u_num_point_shadows) {
            light_shadow *= get_point_shadow(u_light_shadow_slot[i], u_shadow_bias);
        }

        // Apply shadow to diffuse, THEN quantize for PS2 ramp
        float lit = diff * light_shadow;
        if (u_ps2_enabled && u_lighting_ramp_enabled) {
            float steps = float(max(u_lighting_ramp_steps, 1));
            lit = floor(lit * steps + 0.5) / steps;
        }

        total_diffuse += lit * u_light_color[i];

        // Specular (Blinn-Phong)
        vec3 halfway = normalize(light_dir + view_dir);
        float spec = pow(max(dot(norm, halfway), 0.0), 32.0);
        if (u_ps2_enabled && u_specular_banding_enabled) {
            float ssteps = float(max(u_specular_steps, 1));
            spec = floor(spec * ssteps + 0.5) / ssteps;
        }
        total_specular += 0.3 * spec * u_light_color[i] * light_shadow;
    }

    vec3 result = (ambient + total_diffuse + total_specular) * base_color;
    result = mix(result, result + u_highlight_color, u_highlight_strength);
    frag_color = vec4(result, u_alpha);
}
