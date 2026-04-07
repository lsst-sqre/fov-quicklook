#version 300 es
precision highp float;

uniform sampler2D u_texture0;
uniform float u_min;
uniform float u_max;
uniform float u_gamma;
in vec2 v_coord;

out vec4 outputColor;

float scale(float x);
vec3 colormap(float x);

// ↑これらの関数の実装はJavaScript内でこのファイルと連結される。

void main(void) {
    vec2 raw = texture(u_texture0, v_coord).rg;
    float alpha = raw.g;
    // Premultiplied alpha: value チャネルを alpha で割って実値を復元
    float value = alpha > 0.0 ? raw.r / alpha : 0.0;
    float v = scale(value);
    v = clamp(v, 0.f, 1.f);
    outputColor = vec4(colormap(v), alpha);
}

void dummy(void) {
    u_min;
    u_max;
    u_gamma;
}
