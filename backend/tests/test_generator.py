from fastapi.testclient import TestClient
from quicklook.generator.app import app
import pickle
from quicklook.rpc import Rpc

client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def fibonacci_generator(n: int):
    a, b = 1, 1
    for i in range(n):
        yield a
        a, b = b, a + b


def test_rpc():
    rpc = Rpc.create(fibonacci_generator, 5)
    body = pickle.dumps(rpc)
    response = client.post('/rpc', content=body, headers={'Content-Type': 'application/octet-stream'})
    assert response.status_code == 200

    # Deserialize the streaming response
    results = []
    offset = 0
    data = response.content
    while offset < len(data):
        size = int.from_bytes(data[offset : offset + 4], 'big')
        offset += 4
        item = pickle.loads(data[offset : offset + size])
        offset += size
        results.append(item)

    assert results ==  [1, 1, 2, 3, 5]
