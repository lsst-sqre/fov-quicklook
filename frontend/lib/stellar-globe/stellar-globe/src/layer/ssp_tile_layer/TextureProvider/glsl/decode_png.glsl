vec3 decode_png(in vec3 y) {
    //   a = 10000.,
    //   b = -1/8;
    // 
    //   = pack =
    //   y = asinh(a * x) / asinh(a) - b / (1 - b);

    //   = unpack =
    //   x = 1/a * sinh((y + b/(1-b))*asinh(a))

    vec3 x = 0.0001 * sinh(9.903487555 * (y - 0.1111111111));
    return x;
}