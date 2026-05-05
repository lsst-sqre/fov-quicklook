import subprocess
import json
import logging
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, cast

from websockets.sync import client as WebsocketClient
from websockets.sync.connection import Connection as WebsocketConnection

from .base import CommBase

logger = logging.getLogger(__name__)


@dataclass
class HscmapServerCommOptions:
    backend_url: str
    frontend_url: str
    open_browser: bool = False


@dataclass
class QueryResponse:
    query_id: str
    result: str


@dataclass
class QueryResult:
    event: threading.Event
    result: Optional[str] = None


class HscmapServerComm(CommBase):  # pragma: no cover
    _id: str
    _conn: WebsocketConnection
    _on_msg: List[Callable]
    _query_results: Dict[str, QueryResult]
    _recv_thread: threading.Thread

    def __init__(self, initial_msg, options: HscmapServerCommOptions) -> None:
        self._on_msg = []
        self._query_results = {}
        self._options = options
        url = options.backend_url + '/comms'
        self._conn = WebsocketClient.connect(url)
        self._conn.send(json.dumps(initial_msg))
        res: dict = json.loads(self._conn.recv())  # type: ignore
        self._id = res['comm_id']
        if options.open_browser:
            subprocess.check_call(['open', '-a', 'Google Chrome', f'{options.frontend_url}/#{self._id}'])
        else:
            print(f'Open {options.frontend_url}/#{self._id} in your browser')
        self._recv_thread = threading.Thread(target=self._websocket_recv_thread)
        self._recv_thread.start()

    def _websocket_recv_thread(self):
        while True:
            try:
                msg = self._conn.recv()  # will raise exception if connection is closed
            except Exception as e:
                self._cleanup_query_results()
                break
            msg = json.loads(msg)
            if msg['type'] == 'queryResponse':
                self._handle_query_response(
                    QueryResponse(
                        query_id=msg['queryId'],
                        result=msg['content'],
                    ),
                )
                continue
            for callback in self._on_msg:
                callback(msg)

    def send(self, msg):
        self._conn.send(json.dumps(msg))

    def on_msg(self, callback):
        self._on_msg.append(callback)

    def _handle_query_response(self, r: QueryResponse):
        assert r.query_id in self._query_results
        query_result = self._query_results[r.query_id]
        query_result.result = r.result
        query_result.event.set()

    def wait_for_query_response_text(self, query_id: str) -> str:
        assert query_id not in self._query_results
        self._query_results[query_id] = QueryResult(event=threading.Event())
        self._query_results[query_id].event.wait()
        query_result = self._query_results.pop(query_id, None)
        if query_result is None:  # _cleanup_query_results was called
            raise ValueError(f'Query response for {query_id}')
        return cast(str, query_result.result)

    def _cleanup_query_results(self):
        for query_id, query_result in [*self._query_results.items()]:
            query_result.event.set()
            del self._query_results[query_id]

    def close(self):
        self._cleanup_query_results()
        self._conn.close()
        self._recv_thread.join()
