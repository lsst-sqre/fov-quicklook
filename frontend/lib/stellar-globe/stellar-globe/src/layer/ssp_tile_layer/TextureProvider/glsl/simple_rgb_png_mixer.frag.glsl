#version 300 es

precision highp float;

uniform sampler2D  u_texture0, u_texture1, u_texture2;
uniform float u_beta;
uniform float u_a;
uniform float u_bias;
uniform float u_b0;
in      vec2  v_coord;
out     vec4  outputColor;

//@import ./decode_png;
//@import ./simple_rgb;

void main(void){
    vec3 raw = decode_png(vec3(
        texture(u_texture0, v_coord).r,
        texture(u_texture1, v_coord).r,
        texture(u_texture2, v_coord).r
    ));
    vec3 color = simple_rgb(raw, u_beta, u_a, u_bias, u_b0);
    outputColor = vec4(color, 1.);
}