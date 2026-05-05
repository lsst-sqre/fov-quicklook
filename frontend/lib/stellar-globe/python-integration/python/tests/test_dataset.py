import pytest
from hscmap import Window
from hscmap.dataset import parse_hips_properties, HipsDatasetManager, HipsSearchResponse, TileLayer
import requests
import urllib.parse as parse_url


def test_parse_raw_hips_properties():
    raw = 'hips_doi             = 10.26093/cds/aladin/598a-0e\nhips_initial_fov     = 80\nhips_initial_ra      = 291.88185\nhips_initial_dec     = 21.43516\ncreator_did          = ivo://CDS/P/PanSTARRS/DR1/color-i-r-g\ndata_pixel_bitpix    = 16\nhips_sampling        = bilinear\nhips_overlay         = mean\nhips_hierarchy       = mean\nhips_creator         = Boch T. (CDS)\nhips_copyright       = CNRS/Universite de Strasbourg\nobs_title            = PanSTARRS DR1 color (i, r, g)\nobs_collection       = PanSTARRS DR1 color (from bands i, r, g)\nobs_description      = Pan-STARRS is a system for wide-field astronomical imaging developed and operated by the Institute for Astronomy at the University of Hawaii. Pan-STARRS1 (PS1) is the first part of Pan-STARRS to be completed and is the basis for Data Release 1 (DR1).  The PS1 survey used a 1.8 meter telescope and its 1.4 Gigapixel camera to image the sky in five broadband  filters (g, r, i, z, y). The PS1 Science Consortium funded the operation of the Pan-STARRS1 telescope, situated at Haleakala Observatories near the summit of Haleakala in Hawaii, for the purposes of astronomical research. The PS1 consortium is made up of astronomers and engineers from 14 institutions from six countries.\\nPan-STARRS1 has carried out a set of distinct synoptic imaging sky surveys including the 3pi Steradian Survey and the Medium Deep Survey in 5 bands (grizy). The mean 5 sigma point source limiting sensitivities in the stacked 3pi Steradian Survey in grizy are (23.3, 23.2, 23.1, 22.3, 21.4) respectively. The upper bound on the systematic uncertainty in the photometric calibration across the sky is 7-12 millimag depending on the bandpass. The systematic uncertainty of the astrometric calibration using the Gaia frame comes from a comparison of the results with Gaia: the standard deviation of the mean and median residuals (Delta ra, Delta dec ) are (2.3, 1.7) milliarcsec, and (3.1, 4.8) milliarcsec respectively.\nobs_ack              = Images data retrieved from the Mikulski Archive for Space Telescopes (MAST) at STScI. Thanks to Clara Brasseur for her help.\nprov_progenitor      = MAST/STScI\nbib_reference        = 2016arXiv161205560C\nbib_reference_url    = https://ui.adsabs.harvard.edu/?#abs/2016arXiv161205560C\nobs_copyright        = PS1 Science Consortium\nobs_copyright_url    = http://panstarrs.stsci.edu/\nt_min                = 54995.492683057\nt_max                = 57062.0827910156\nobs_regime           = Optical\n# PanSTARRS filters are described at http://svo2.cab.inta-csic.es/svo/theory/fps/index.php?mode=browse&gname=PAN-STARRS\nem_min               = 3.94340e-7\nem_max               = 8.430e-7\nclient_category      = Image/Optical/PanSTARRS\nhips_builder         = Aladin/HipsGen v10.138\nhips_version         = 1.4\nhips_release_date    = 2019-11-21T15:37Z\nhips_frame           = equatorial\nhips_order           = 11\nhips_tile_width      = 512\n#hips_service_url    = ex: http://yourHipsServer/PanSTARRS DR1 color-i-r-g\nhips_status          = public master clonableOnce\nhips_tile_format     = jpeg\nhips_data_range      = -2.323 7.915\nhips_pixel_scale     = 4.473E-4\ns_pixel_scale        = 6.944E-5\ndataproduct_type     = image\nmoc_sky_fraction     = 0.76386\nhips_estsize         = 3825176\nhipsgen_date         = 2018-11-12T17:48Z\nhipsgen_params       = tiles\nhips_creation_date   = 2018-11-12T17:48Z\nhips_order_min       = 0\nhipsgen_date_1       = 2019-05-20T09:35Z\nhipsgen_params_1     = out=/asd-volumes/sc1-asd-volume7/Pan-STARRS/DR1/y UPDATE\nhipsgen_date_2       = 2019-11-21T15:00Z\nhipsgen_params_2     = out=/asd-volumes/sc1-asd-volume7/CDS_P_PanSTARRS_DR1_color-i-r-g color=true method=mean tree\nhipsgen_date_3       = 2019-11-21T15:10Z\nhipsgen_params_3     = out=/asd-volumes/sc1-asd-volume7/CDS_P_PanSTARRS_DR1_color-i-r-g color=true method=mean tree\nhipsgen_date_4       = 2019-11-21T15:27Z\nhipsgen_params_4     = out=/asd-volumes/sc1-asd-volume7/CDS_P_PanSTARRS_DR1_color-i-r-g color=true method=mean tree\ndataproduct_subtype  = color\nhipsgen_date_5       = 2019-11-21T15:37Z\nhipsgen_params_5     = out=/asd-volumes/sc1-asd-volume7/CDS_P_PanSTARRS_DR1_color-i-r-g color=true method=mean tree\n'
    parsed = parse_hips_properties(raw)
    parsed_dict = {key: value for key, value in parsed}
    assert parsed_dict['hips_doi'] == '10.26093/cds/aladin/598a-0e'


def test_dataset_tile_layers(w: Window):
    assert isinstance(w.dataset.tile_layers, dict)


@pytest.fixture
def tile_layer(w: Window):
    return w.dataset.tile_layers['PDR3 DUD']


def test_tile_layer_visible(tile_layer: TileLayer):
    assert tile_layer.visible is True


def test_tile_layer_visible_set(tile_layer: TileLayer):
    assert tile_layer.visible is True
    tile_layer.visible = False
    # ↓の行のtile_layer.visibleのgetterでsyncが起きている
    assert tile_layer.visible is False


def test_hips_base_url_get(w: Window):
    assert w.dataset.hips.base_url is None


panstarrs_url = 'https://alasky.cds.unistra.fr/Pan-STARRS/DR1/color-i-r-g'


def test_hips_base_url_set(w: Window):
    w.dataset.hips.base_url = panstarrs_url
    assert w.dataset.hips.base_url == panstarrs_url


def test_hips_clear(w: Window):
    w.dataset.hips.base_url = panstarrs_url
    assert w.dataset.hips.base_url == panstarrs_url
    w.dataset.hips.clear()
    assert w.dataset.hips.base_url is None


def test_hips_properties_with_no_base_url(w: Window):
    w.dataset.hips.base_url = None
    assert w.dataset.hips.properties is None


@pytest.mark.slow
def test_hips_properties(w: Window):
    w.dataset.hips.base_url = panstarrs_url
    assert w.dataset.hips.properties is not None


@pytest.mark.slow
def test_hips_find_by_name(w: Window):
    response = w.dataset.hips.find_by_name('PanSTARRS')
    assert isinstance(response, list)
    assert isinstance(response[0], HipsSearchResponse)
    result = {r.obs_title: r for r in response}['PanSTARRS DR1 color (i, r, g)']
    assert result.hips_service_url == panstarrs_url
