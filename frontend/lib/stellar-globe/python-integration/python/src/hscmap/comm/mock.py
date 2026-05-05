# To run mock-comm server,
#
# cd ./mock-comm-server
# npm run dev

from dataclasses import dataclass
from .base import CommBase, remove_none
from typing import Any, Callable, List
import requests


@dataclass
class MockCommOptions:
    base_url: str


class MockComm(CommBase):
    _id: str
    _base_url: str

    _on_msg: List[Callable]
    _sent_history: List[Any]

    def __init__(
        self,
        initial_msg: Any,
        options: MockCommOptions,
    ):
        self._id = initial_msg['id']
        self._base_url = options.base_url
        self._on_msg = []
        self._sent_history = []
        r = requests.post(f'{self._base_url}/comms/', json=remove_none(initial_msg))
        r.raise_for_status()

    def send(self, msg: Any) -> None:
        r = requests.post(f'{self._base_url}/comms/{self._id}', json=remove_none(msg))
        self._sent_history.append(msg)
        r.raise_for_status()

    def on_msg(self, callback: Callable) -> None:
        self._on_msg.append(callback)

    def wait_for_query_response_text(self, query_id: str) -> Any:
        r = requests.get(f'{self._base_url}/comms/{self._id}/queryResponse/{query_id}', headers={'Accept': 'text/plain'})
        if r.status_code == 200:  # pragma: no branch
            return r.text

    def pull_message(self):  # This method is for testing purposes only
        r = requests.get(f'{self._base_url}/comms/{self._id}/messages/first')
        if r.status_code == 200:
            msg = r.json()
            for callback in self._on_msg:
                callback(msg)
            return True
        return False

    def pull_all_messages(self):  # This method is for testing purposes only
        while self.pull_message():
            pass

    def last_outgoing_message(self) -> Any:
        return self._sent_history[-1]
