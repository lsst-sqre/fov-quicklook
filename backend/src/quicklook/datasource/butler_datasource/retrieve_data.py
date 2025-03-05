from lsst.resources import ResourcePath


def retrieve_data(uri: ResourcePath) -> bytes:  # pragma: no cover
    return uri.read()
