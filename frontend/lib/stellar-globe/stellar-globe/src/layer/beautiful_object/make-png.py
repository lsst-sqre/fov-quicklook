import numpy
import astropy.io.fits as afits
from PIL import Image
import argparse

Image.MAX_IMAGE_PIXELS = 50000 * 50000


np = numpy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', '-o', required=True)
    args = parser.parse_args()

    rgb_array = mix(m31)[::-1, :, ::1]
    scaled_array = (rgb_array * 255).astype(np.uint8)
    image = Image.fromarray(scaled_array)
    image.save(args.out)


def mix(params):
    u_a = numpy.array(params['a'])
    u_b = numpy.array(params['b'])
    u_beta = numpy.array(params['beta'])
    u_bias = numpy.array(params['bias'])
    u_gamma = params['gamma']
    u_exposure = params['exposure']
    u_ground = params['ground']
    u_mix = numpy.array(params['mix']).reshape((4, 3))

    image0 = afits.open('./HSC-I.fits')[0].data  # type: ignore
    image1 = afits.open('./HSC-R.fits')[0].data  # type: ignore
    image2 = afits.open('./HSC-G.fits')[0].data  # type: ignore
    image3 = afits.open('./ha.fits')[0].data  # type: ignore

    source = numpy.array([image0, image1, image2, image3][::1]).T
    source = u_a * (source + u_b)
    source = numpy.arcsinh(u_beta * source) / numpy.arcsinh(u_beta) + u_bias
    source = numpy.clip(source, 0., 1.)
    source = -0.5 * (numpy.cos(numpy.pi * numpy.clip(source, 0., 1.)) - 1.0)
    H = source.shape[0]
    W = source.shape[1]
    A = u_mix
    x = source
    rgb = (A.T @ x.reshape((-1, 4)).T).T.reshape((H, W, 3))
    rgb = (u_exposure * numpy.clip(rgb + u_ground, 0., 1.)) ** u_gamma
    return rgb.transpose((1, 0, 2))


m31 = {
    'nFilters': 4,
    'a': [2.199295029536234, 2.0103885194367055, 1.9841269841269842, 2.022793120413001],
    'b': [-0.001648548459980411, -0.0025677667840354867, -0.0033194448390797488, -0.01946514951398076],
    'mix': [
        0.2, 0, 0,
        0, 1, 0,
        0, 0, 1,
        0.8, 0, 0],
    'beta': [12.058291997314814, 43.60555950912844, 83.93141691026881, 65.15882757731914],
    'bias': [0, 0, 0, 0],
    'exposure': 1,
    'gamma': 1,
    'ground': 0,
    'view': {
        'a': 0.18668047898454176,
        'd': 0.720410877137467,
        'fovy': 0.013242880368563102,
        'roll': -2.1982248398339577,
    },
}


main()
