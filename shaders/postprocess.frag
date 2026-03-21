#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform sampler2D u_scene;
uniform vec2 u_resolution;

uniform bool u_ps2_enabled;

uniform int u_pixel_size;          // screen pixels per block
uniform bool u_quantize_enabled;
uniform int u_quantize_steps;      // per-channel steps
uniform bool u_dither_enabled;

float bayer4(vec2 p) {
    // 4x4 Bayer matrix scaled to [0,1)
    int x = int(mod(p.x, 4.0));
    int y = int(mod(p.y, 4.0));
    int i = x + y * 4;
    // Row-major values
    int m[16] = int[16](
        0,  8,  2, 10,
        12, 4, 14, 6,
        3, 11, 1, 9,
        15, 7, 13, 5
    );
    return float(m[i]) / 16.0;
}

vec3 quantize(vec3 c, float steps) {
    return floor(c * steps + 0.5) / steps;
}

void main() {
    vec2 uv = v_uv;

    if (u_ps2_enabled) {
        // Pixelation based on screen pixel blocks, independent of window size.
        vec2 frag = gl_FragCoord.xy;
        float ps = float(max(u_pixel_size, 1));
        vec2 snapped = (floor(frag / ps) * ps) + vec2(0.5) * ps;
        uv = snapped / u_resolution;
    }

    vec3 color = texture(u_scene, uv).rgb;

    if (u_ps2_enabled && u_quantize_enabled) {
        float steps = float(max(u_quantize_steps, 2));
        if (u_dither_enabled) {
            // Small pre-quantization bias to create ordered dithering.
            float d = bayer4(gl_FragCoord.xy) - 0.5;
            color += d / steps;
        }
        color = quantize(clamp(color, 0.0, 1.0), steps);
    }

    frag_color = vec4(color, 1.0);
}

