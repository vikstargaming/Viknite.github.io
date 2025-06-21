import asyncio
import websockets
import json

connected = set()
players = {}

async def handler(websocket):
    connected.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)

            # Update player info
            if data["type"] == "update":
                players[data["id"]] = data
                # Broadcast all players to everyone
                msg = json.dumps({"type": "players", "players": players})
                await asyncio.wait([ws.send(msg) for ws in connected])

            # Relay build or shoot events to others
            elif data["type"] in ["build", "shoot"]:
                msg = json.dumps(data)
                await asyncio.wait([ws.send(msg) for ws in connected if ws != websocket])

    finally:
        connected.remove(websocket)
        # Remove player on disconnect
        disconnected = None
        for pid, p in players.items():
            if p["ws"] == websocket:
                disconnected = pid
                break
        if disconnected:
            del players[disconnected]
            msg = json.dumps({"type": "remove", "id": disconnected})
            await asyncio.wait([ws.send(msg) for ws in connected])

async def main():
    async with websockets.serve(handler, "localhost", 6789):
        print("Server started on ws://localhost:6789")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
