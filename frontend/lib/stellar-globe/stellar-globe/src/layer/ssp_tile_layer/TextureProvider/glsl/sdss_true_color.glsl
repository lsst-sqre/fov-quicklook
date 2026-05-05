float scale(in float x, in float beta) {
    return asinh(beta * x) / asinh(beta);
}

vec3 sdss_true_color(in vec3 raw, in float beta, in float a, in float bias, in float b0) {
    raw += b0;
    float i = (raw.r + raw.g + raw.b) / 3.;
    vec3 color = scale(i, beta) / i * raw;
    color = a * color + bias;
    return color;
}
