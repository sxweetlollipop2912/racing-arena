import asyncio
import queue
from typing import Optional, Tuple, List
from globals import LOGGER


class ConnectionManager:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        if not hasattr(self, "writer"):
            self.writer: Optional[asyncio.StreamWriter] = None
            self.messages: queue.Queue = queue.Queue()

    async def write_to_server(self, message: str) -> None:
        byte_message: bytes = (message + "\n").encode()
        self.writer.write(byte_message)
        await self.writer.drain()

    async def send_ready_signal(self) -> None:
        LOGGER.info("[Connection Thread] Sending READY signal to server.")
        await self.write_to_server("READY")

    async def send_unready_signal(self) -> None:
        LOGGER.info("[Connection Thread] Sending UNREADY signal to server.")
        await self.write_to_server("UNREADY")

    async def send_answer(self, answer: int) -> None:
        LOGGER.info(f"[Connection Thread] Sending answer to server: {answer}")
        await self.write_to_server(f"ANSWER;{answer}")

    async def send_registration(self, nickname: str) -> None:
        LOGGER.info(
            f"[Connection Thread] Sending REGISTER signal to server: {nickname}"
        )
        await self.write_to_server(f"REGISTER;{nickname}")

    async def handle_conversation(self, host: str, port: int) -> None:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            self.writer = writer

            address: Tuple[str, int] = writer.get_extra_info("peername")
            LOGGER.info(f"[Connection Thread] Accepted connection from {address}.")
            while True:
                data: bytes = await reader.readline()
                if not data:
                    break
                message: str = data.decode().strip()
                LOGGER.info(
                    f"[Connection Thread] Received message from {address}: {message}"
                )

                command: str
                args: List[str]
                command, *args = message.split(";")
                command = command.upper()
                self.messages.put((command, args))

                LOGGER.info(
                    f"[Connection Thread] Received message from {address}: {message}"
                )

        except ConnectionResetError:
            LOGGER.info(
                f"[Connection Thread] Connection reset by peer, address {address}."
            )
        finally:
            self.writer = None
            writer.close()
