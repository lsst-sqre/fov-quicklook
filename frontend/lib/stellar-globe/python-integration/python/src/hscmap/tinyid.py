import secrets


def tinyid(length: int = 16):
    return secrets.token_urlsafe(length)
