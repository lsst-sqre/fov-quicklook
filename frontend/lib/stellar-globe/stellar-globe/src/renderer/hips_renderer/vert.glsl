precision mediump float;
attribute  vec2   a_coord;
uniform    mat4   u_pvMatrix;
uniform    mat3   u_rotMatrix;
uniform    mat3   u_tMatrix;
uniform    float  u_belt_end;
uniform    mat4   u_ax, u_ay, u_az;
uniform    mat4   u_bx, u_by, u_bz;
varying    vec2   v_coord;
varying    float  v_w;


void main(void) {
    float p = a_coord.x;
    float q = a_coord.y;
    float p2 = p*p,  q2 = q*q;
    float p3 = p2*p, q3 = q2*q;
    float p4 = p3*p, q4 = q3*q;
    vec4 P = vec4(p3, p2, p, 1.);
    vec4 Q = vec4(q3, q2, q, 1.);
    vec3 position;
    vec3 a = vec3(
        dot(P, u_ax * Q),
        dot(P, u_ay * Q),
        dot(P, u_az * Q)
    );
    vec3 b = vec3(
        dot(P, u_bx * Q),
        dot(P, u_by * Q),
        dot(P, u_bz * Q)
    );
    position = mix(a, b, step(0., u_belt_end * (q - p) - 1./128.));
    gl_Position = u_pvMatrix * vec4(u_rotMatrix * position, 1.);
    v_coord = a_coord;
    v_w = gl_Position.w;
}