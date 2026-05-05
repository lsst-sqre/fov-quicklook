#version 300 es

in     vec2   a_coord;
out    vec2   v_coord;

void main(void) {
    gl_Position = vec4(2. * a_coord - vec2(1.), 0., 1.);
    v_coord = a_coord;
}