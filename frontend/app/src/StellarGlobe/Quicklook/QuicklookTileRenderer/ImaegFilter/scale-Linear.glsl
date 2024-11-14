// Linear

float scale(float raw) {
  float x = max(0., (raw - u_min) / (u_max - u_min));
  x = pow(x, exp(-u_gamma));
  return x;
}
