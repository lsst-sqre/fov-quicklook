def getLogger(name: str):
    import logging

    return logging.getLogger(f'uvicorn.quicklook.{name}')
