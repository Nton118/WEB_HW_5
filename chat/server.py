import aiofile
import aiopath
import asyncio
import logging
import os
import names
import sys
import time
import websockets
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK

logging.basicConfig(level=logging.INFO)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

import currency


class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f"{ws.remote_address} connects")

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f"{ws.remote_address} disconnects")

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def log_exc_request(self, name: str, days: int, curr: list) -> None:
        log_file_path = aiopath.AsyncPath("log.txt")
        async with aiofile.AIOFile(log_file_path, "a") as log_file:
            if not await log_file_path.exists():
                await log_file_path.touch()

            await log_file.write(f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))} {name}: {days}, {curr}\n')

    async def send_exc_rates(self, message: str, ws: WebSocketServerProtocol):
        args = message.split()[1:]
        days = int(args[0]) if len(args) >= 1 else 1
        curr = args[1:] if len(args) >= 2 else ['EUR', 'USD']
        if days > 10:
            await ws.send('Sorry, max 10 past days data is available!')
            days = 10
        rates = await currency.collect_cur_rates(days=days, currencies=curr)
        await self.log_exc_request(ws.name, days, curr)
        lines = currency.format_output(rates).split("\n")
        for line in lines:
            await ws.send(line)

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distribute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distribute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if message.lower().lstrip().startswith("exchange"):
                await self.send_exc_rates(message, ws)
            else:
                await self.send_to_clients(f"{ws.name}: {message}")


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, "localhost", 8080):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
