from fastapi import FastAPI

app = FastAPI()


@app.get("/healthz")
async def route_healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get('/quicklooks')
async def route_create_quicklook():
    pass
