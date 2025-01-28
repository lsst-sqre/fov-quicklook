from lsst.resources import ResourcePath


def retrieve_data(uri: ResourcePath) -> bytes:
    return uri.read()
