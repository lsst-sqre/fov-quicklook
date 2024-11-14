// Linear

float scale(float raw) {
  float x = (raw - u_min) / (u_max - u_min);
  float y = exp(u_gamma);
  x = asinh(y * x) / asinh(y);
  return x;
}
