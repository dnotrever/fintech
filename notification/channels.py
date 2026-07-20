from typing import Protocol


class EmailChannel(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...

