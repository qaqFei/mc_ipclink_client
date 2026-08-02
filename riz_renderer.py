import argparse
import time

from renderer import Renderer

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--data-path", type=str, required=True)
arg_parser.add_argument("--music-path", type=str, required=True)
args = arg_parser.parse_args()

frames = []
current_frame = []

dataf = open(args.data_path, "r")
for line in dataf:
    line = line.strip()
    if line == "!":
        current_frame.append(f"tp qaqFei 3.28 {-55 + 0.25 + 0.01 * len(frames)} 1.883")
        frames.append(current_frame)
        current_frame = []
    
    current_frame.append(line)
    
renderer = Renderer()

for frame in frames:
    renderer._commands = frame
    renderer._commandsRun()
    renderer._updateFrameCounter()
    time.sleep(0.75)
