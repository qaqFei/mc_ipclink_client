import time

import midi_parse # midi_parse==0.0.8

import minecraft_ipclink

minecraft_ipclink.ShmSocket.setBusywait(True)

def get_type(note: int):
    note = note if 30 <= note <= 102 else (30 if note < 30 else 102)
    typemap = sorted([
        ("bass", 30, 2),
        ("guitar", 42, 1),
        ("pling", 54, 1),
        ("xylophone", 78, 5),
    ], reverse=True)
    for name, start, num in typemap:
        if start <= note <= start + 24:
            return name, 2 ** ((-12 + note - start) / 12), num
            
client = minecraft_ipclink.IPCLinkClient("midi_player")
client.runForever(inOtherThread=True)

print("tip: it is executed at @e[tag=midi_player]")

commands = []
            
while True:
    try:
        path = input(">> ")
        mid = midi_parse.MidiFile(open(path, "rb").read())
        more_delta = 0.0
        
        for msg in mid.play():
            dt = msg["global_sec_delta"] - more_delta
            time.sleep(max(dt, 0.0))
            t = time.perf_counter()
            print(f"\rnow time: {msg["sec_time"]:.2f}s / {mid.second_length:.2f}s", end="")
            
            commands.clear()
            
            match msg["type"]:
                case "note_on":
                    name, note, num = get_type(msg["note"])
                    vol = msg["velocity"] / 127
                    command = f"execute at @e[tag=midi_player] run playsound minecraft:block.note_block.{name} block @a ~ ~ ~ {vol} {note} {vol}"
                    for _ in range(num): commands.append(command)
            
            client.runCommands(commands)
            
            more_delta = time.perf_counter() - t
    except KeyboardInterrupt:
        continue
