from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import asyncio
import websockets
import threading
import json
import uuid

app = Ursina()
window.color = color.azure

# Unique player ID
player_id = str(uuid.uuid4())

# Networking globals
players = {}
bullets = []
walls = []

score = 0

class MultiplayerPlayer(Entity):
    def __init__(self, player_id):
        super().__init__(model='cube', color=color.blue, scale=1.5)
        self.player_id = player_id

    def update(self, pos, rot):
        self.position = pos
        self.rotation = rot

class Bullet(Entity):
    def __init__(self, position, direction):
        super().__init__(model='sphere', color=color.yellow, scale=0.2, position=position)
        self.direction = direction

    def update(self):
        self.position += self.direction * 0.5
        # Check collision with enemies or walls can be added here
        if distance(self, camera) > 100:
            destroy(self)
            bullets.remove(self)

class Wall(Entity):
    def __init__(self, pos):
        super().__init__(model='cube', scale=(2,2,0.2), color=color.brown, position=pos, collider='box')

player = FirstPersonController(y=2)
ground = Entity(model='plane', scale=100, color=color.green, collider='box')
Sky()
score_text = Text(text='Score: 0', position=(-0.85, 0.45), scale=2)

def shoot():
    direction = camera.forward
    bullet = Bullet(position=player.position + Vec3(0,1.5,0), direction=direction)
    bullets.append(bullet)
    # Send shoot event
    asyncio.run_coroutine_threadsafe(send_message({
        "type": "shoot",
        "id": player_id,
        "position": list(bullet.position),
        "direction": list(direction)
    }), loop)

def build_wall():
    pos = player.position + camera.forward * 3
    wall = Wall(pos=pos)
    walls.append(wall)
    # Send build event
    asyncio.run_coroutine_threadsafe(send_message({
        "type": "build",
        "id": player_id,
        "position": list(pos)
    }), loop)

def update_score():
    global score
    score += 1
    score_text.text = f'Score: {score}'

async def send_message(msg):
    if websocket is not None:
        await websocket.send(json.dumps(msg))

async def recv_handler():
    global players
    async for message in websocket:
        data = json.loads(message)
        if data["type"] == "players":
            for pid, pdata in data["players"].items():
                if pid == player_id:
                    continue
                pos = Vec3(*pdata["pos"])
                rot = Vec3(*pdata["rot"])
                if pid not in players:
                    players[pid] = MultiplayerPlayer(pid)
                players[pid].position = pos
                players[pid].rotation = rot
        elif data["type"] == "build":
            pos = Vec3(*data["position"])
            Wall(pos=pos)
        elif data["type"] == "shoot":
            # Could add bullet effects here from other players
            pass
        elif data["type"] == "remove":
            pid = data["id"]
            if pid in players:
                destroy(players[pid])
                del players[pid]

async def network_loop():
    global websocket
    uri = "ws://localhost:6789"
    async with websockets.connect(uri) as ws:
        websocket = ws
        # Send player init info
        while True:
            pos = list(player.position)
            rot = list(player.rotation)
            msg = {"type": "update", "id": player_id, "pos": pos, "rot": rot}
            await websocket.send(json.dumps(msg))
            await asyncio.sleep(0.05)

# Run network loop in background thread
def start_network():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(network_loop())

threading.Thread(target=start_network, daemon=True).start()

def input(key):
    if key == 'left mouse down':
        shoot()
    if key == 'b':
        build_wall()

app.run()
