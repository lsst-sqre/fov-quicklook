precision mediump float;
uniform float u_alpha;
varying vec4 v_color;

void main() {
    gl_FragColor = v_color;
    gl_FragColor.a *= u_alpha;
}