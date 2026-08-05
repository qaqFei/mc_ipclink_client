import argparse
import typing
import json
import time

import midi_parse # midi_parse==0.0.8

import minecraft_ipclink

minecraft_ipclink.ShmSocket.setBusywait(True)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--origin", type=str, help="origin position for building, format: x,y,z", required=True)
arg_parser.add_argument("--stepper", type=str, help="position step for building", default="lambda x, z: (x, z)")
arg_parser.add_argument("--midi", type=str, help="midi file to build", required=True)
arg_parser.add_argument("--builder", type=str, help="the builder player", required=True)
arg_parser.add_argument("--tick-speed", type=float, help="the tick speed for game", default=1.0)
args = arg_parser.parse_args()

client = minecraft_ipclink.IPCLinkClient("midi_builder")
client.runForever(inOtherThread=True)

ox, oy, oz = map(int, args.origin.split(","))
stepper: typing.Callable[[int, int], tuple[int, int]] = eval(args.stepper)
blocks: list[tuple[tuple[int, int, int], str]] = []
currentSignalPosition = (3, 1, 0)
buildBaseBlock = "minecraft:white_concrete"
redStoneTickTime = 2 / 20 / args.tick_speed # 2gt
noteBuckets: list[list[int]] = []
xFacing = "west" if stepper(1, 0)[0] != 0 else "north"

with open(args.midi, "rb") as f:
    mid = midi_parse.MidiFile(f.read())

for msg in mid.play():
    if msg["type"] != "note_on": continue
    if msg["velocity"] <= 0: continue
    
    bucketIndex = int(msg["sec_time"] / redStoneTickTime)
    while len(noteBuckets) <= bucketIndex: noteBuckets.append([])
    noteBuckets[bucketIndex].append(msg["note"])

def getPosition(x: int, y: int, z: int):
    dx, dz = stepper(x, z)
    return ox + dx, oy + y, oz + dz

def addPosition(p: tuple[int, int, int], dx: int, dy: int, dz: int):
    return p[0] + dx, p[1] + dy, p[2] + dz

def addBlock(x: int, y: int, z: int, block: str):
    blocks.append((getPosition(x, y, z), block))

def get_type(note: int):
    note = min(102, max(30, note))
    
    typemap = [
        ("minecraft:bookshelf", 30, 2),
        ("minecraft:white_wool", 42, 1),
        ("minecraft:glowstone", 54, 1),
        ("minecraft:bone_block", 78, 5),
    ]
    
    for name, start, num in typemap:
        if start <= note <= start + 24:
            return name, note - start, num
    
    assert False
    
addBlock(0, 0, 0, buildBaseBlock)
addBlock(0, 1, 0, f"minecraft:stone_button[face=floor, facing={xFacing}]")
addBlock(1, 0, 0, buildBaseBlock)
addBlock(1, 1, 0, "minecraft:redstone_wire")
addBlock(2, 1, 0, buildBaseBlock)
addBlock(2, 2, 0, "minecraft:redstone_wire")

delayUsed = 0

for bucketIndex, bucket in enumerate(noteBuckets):
    if delayUsed > 0:
        delayUsed -= 1
        continue
    
    addBlock(*addPosition(currentSignalPosition, 0, 0, 0), buildBaseBlock)
    addBlock(*addPosition(currentSignalPosition, 0, 1, 0), "minecraft:redstone_wire")
    
    types = []
    for i in bucket:
        name, pitch, num = get_type(i)
        types.extend([(name, pitch)] * num)
    
    types.append((None, None))
    
    for i, (note, pitch) in enumerate(types):
        group, gindex = i // 28, i % 28
        dz = (gindex + 1) if gindex <= 13 else -(gindex - 13)
        dx = group * 3
        
        if gindex == 0:
            for j in range(3):
                addBlock(*addPosition(currentSignalPosition, dx + j, 0, 0), buildBaseBlock)
                addBlock(*addPosition(currentSignalPosition, dx + j, 1, 0), "minecraft:redstone_wire")
        
        addBlock(*addPosition(currentSignalPosition, dx, 0, dz), buildBaseBlock)
        addBlock(*addPosition(currentSignalPosition, dx, 1, dz), "minecraft:redstone_wire")
        
        if note is not None:
            addBlock(*addPosition(currentSignalPosition, dx + 1, -1, dz), note)
            addBlock(*addPosition(currentSignalPosition, dx + 1, 0, dz), f"minecraft:note_block[note={pitch}]")
        else:
            addBlock(*addPosition(currentSignalPosition, dx + 1, 0, dz), f"command_block{json.dumps({'Command': f"tp @e[tag=midi_player] {' '.join(map(str, addPosition(currentSignalPosition, ox, oy + 2, oz)))}"})}")
    
    dx = (len(bucket) // 28) * 3
    if len(bucket) % 28 > 0: dx += 2
    addBlock(*addPosition(currentSignalPosition, dx, 0, 0), buildBaseBlock)
    
    delay = 1
    while delay < 4 and bucketIndex + delay < len(noteBuckets) and not noteBuckets[bucketIndex + delay]:
        delay += 1
        delayUsed += 1
        
    addBlock(*addPosition(currentSignalPosition, dx, 1, 0), f"minecraft:repeater[facing={xFacing},delay={delay}]")
    
    currentSignalPosition = addPosition(currentSignalPosition, dx + 1, 0, 0)
    
blockPositions = set((x, y, z) for (x, y, z), *_ in blocks)
airBlockPositions = set()

for x, y, z in blockPositions:
    for i in range(-1, 2):
        for j in range(-1, 2):
            for k in range(-1, 2):
                airBlockPositions.add((x + i, y + j, z + k))

blocks.extend((pos, "minecraft:air") for pos in airBlockPositions if pos not in blockPositions)

commandPacketSize = 512

commands = []
for (x, y, z), state in blocks:
    if len(commands) % commandPacketSize == 0:
        commands.append(f"tp {args.builder} {x} {y} {z}")
        
    commands.append(f"setblock {x} {y} {z} {state}")

commands.append("say building done")

for i in range(0, len(commands), commandPacketSize):
    client.runCommands(commands[i:i + commandPacketSize])
    time.sleep(1 / 120)
    print(f"Sent {i} commands")
    
client.close()
