precision mediump float;
uniform   sampler2D  u_texture;
uniform   float      u_alpha;
uniform   vec4       u_color;
varying   vec2       v_tCoord;
varying   vec4       v_color;

void main() {
    gl_FragColor = u_color * v_color * texture2D(u_texture, v_tCoord);
    gl_FragColor.a *= u_alpha;
}