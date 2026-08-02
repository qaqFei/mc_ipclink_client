import argparse
import json

import tqdm

from renderer import Triangle, Renderer

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--data-path", type=str, required=True)
arg_parser.add_argument("--output-path", type=str, required=True)
args = arg_parser.parse_args()

frames = []
current_frame = []

dataf = open(args.data_path, "r")
for line in dataf:
    line = line.strip()
    if not line: continue
    
    if line == "!":
        frames.append(current_frame)
        current_frame = []
        
        if len(frames) % 600 == 0:
            print(f"Loaded {len(frames)} frames")
        
        if len(frames) > 6000:
            break
        
        continue
    
    tokens = tuple(filter(bool, line.split(",")))
    
    if tokens[0] == "circ":
        current_frame.append((
            "circ",
            tuple(map(float, tokens[1:3])),
            float(tokens[3]), float(tokens[4]) * 2.0,
            tuple(map(float, tokens[5:9]))
        ))
    elif tokens[0] == "lineSet":
        tris = []
        current_frame.append(("tris", tris))
        for i in range(1, len(tokens), 18):
            tris.append(Triangle(
                p1 = tuple(map(float, tokens[i:i+2])),
                p2 = tuple(map(float, tokens[i+6:i+2+6])),
                p3 = tuple(map(float, tokens[i+12:i+2+12])),
                color = tuple(map(float, tokens[i+2:i+6]))
            ))
            
            tris.append(None)
    elif tokens[0] == "lineRing":
        current_frame.append((
            "lineRing",
            tuple(map(float, tokens[1:3])),
            float(tokens[3]), float(tokens[4]) * 2.0,
            tuple(map(float, tokens[5:9]))
        ))
    elif tokens[0] == "notePartSet":
        parts = []
        current_frame.append(("notePartSet", parts))
        
        i = 1
        while i < len(tokens):
            typ = tokens[i]; i += 1
            
            if typ == "1":
                parts.append((
                    "circ",
                    tuple(map(float, tokens[i:i+2])),
                    float(tokens[i+2]) / 2.0, 0.0,
                    tuple(map(float, tokens[i+3:i+7]))
                ))
                
                i += 7
            else:
                parts.append((
                    "rect",
                    tuple(map(float, tokens[i:i+2])),
                    tuple(map(float, tokens[i+2:i+4])),
                    tuple(map(float, tokens[i+4:i+8]))
                ))
                
                i += 8

f = open(args.output_path, "w", buffering=2)
renderer = Renderer()
renderer._swap_size = 1
renderer.viewport.size = (0.01, 0.01)

for i, frame in tqdm.tqdm(enumerate(frames)):
    renderer.triangles.clear()
    
    for obj in frame:
        if obj[0] == "circ":
            renderer.addRing(*obj[1:])
            renderer.nextLayer()
        elif obj[0] == "tris":
            renderer.triangles.extend(obj[1])
        elif obj[0] == "lineRing":
            renderer.addRing(*obj[1:])
            renderer.nextLayer()
        elif obj[0] == "notePartSet":
            for part in obj[1]:
                if part[0] == "circ":
                    renderer.addRing(*part[1:])
                elif part[0] == "rect":
                    renderer.addRect(*part[1:])
                    
                renderer.nextLayer()
    
    renderer.viewport.height += 0.01
    
    renderer._renderGenerateCommands()
    for cmd in renderer._commands:
        f.write(cmd)
        f.write("\n")
    f.write("!\n")
    
    renderer._commandsClear()    
    renderer._updateFrameCounter()
    
    frames[i] = None

f.close()
