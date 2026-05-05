#version 300 es
#define M_PI 3.14159265358979323846264
precision highp float;
uniform sampler2D  u_texture0;
uniform sampler2D  u_texture1;
uniform sampler2D  u_texture2;
uniform sampler2D  u_texture3;
uniform vec4       u_a;
uniform vec4       u_b;
uniform vec4       u_beta;
uniform vec4       u_bias;
uniform mat4       u_mix;
uniform float      u_exposure;
uniform float      u_gamma;
uniform float      u_ground;
in vec2            v_coord;
out vec4           outputColor;


void main(void){
    vec4 source = vec4(
        texture(u_texture0, v_coord).r,
        texture(u_texture1, v_coord).r,
        texture(u_texture2, v_coord).r,
        texture(u_texture3, v_coord).r
    );
    source = u_a * (source + u_b);
    source = asinh(u_beta * source) / asinh(u_beta) + u_bias;
    source = clamp(source, 0., 1.);
    source = -0.5 * (cos(M_PI * clamp(source, 0., 1.)) - 1.0);
    vec3 rgb = (u_mix * source).rgb;
    rgb = pow(u_exposure * max(vec3(0.), (rgb + u_ground)), vec3(u_gamma));
    outputColor.rgb = rgb;
    outputColor.a = 1.;
}
