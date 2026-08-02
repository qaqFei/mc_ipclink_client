from __future__ import annotations

import dataclasses
import json
import typing
import math

import minecraft_ipclink

minecraft_ipclink.ShmSocket.setBusywait(True)

def _cvtColor(color: tuple[float, float, float, float]) -> int:
    color = tuple(map(lambda x: int(max(0.0, min(1.0, x) * 255)), color))
    argb = (color[3] << 24) | (color[0] << 16) | (color[1] << 8) | color[2]
    if argb > 0x80000000: argb -= 0x100000000
    return argb

class Matrix44:
    def __init__(self, data: typing.Optional[list[float] | Matrix44] = None):
        if data is None:
            self.mat = [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0
            ]
        elif isinstance(data, Matrix44):
            self.mat = data.mat.copy()
        else:
            if len(data) != 16:
                raise ValueError("Matrix44 requires exactly 16 floats")
            
            self.mat = data
    
    def copy(self):
        return Matrix44(self)
    
    def transform(self, other: Matrix44):
        self.mat = [
            self.mat[0*4+0]*other.mat[0*4+0] + self.mat[1*4+0]*other.mat[0*4+1] + self.mat[2*4+0]*other.mat[0*4+2] + self.mat[3*4+0]*other.mat[0*4+3],  # i=0,j=0
            self.mat[0*4+1]*other.mat[0*4+0] + self.mat[1*4+1]*other.mat[0*4+1] + self.mat[2*4+1]*other.mat[0*4+2] + self.mat[3*4+1]*other.mat[0*4+3],  # i=0,j=1
            self.mat[0*4+2]*other.mat[0*4+0] + self.mat[1*4+2]*other.mat[0*4+1] + self.mat[2*4+2]*other.mat[0*4+2] + self.mat[3*4+2]*other.mat[0*4+3],  # i=0,j=2
            self.mat[0*4+3]*other.mat[0*4+0] + self.mat[1*4+3]*other.mat[0*4+1] + self.mat[2*4+3]*other.mat[0*4+2] + self.mat[3*4+3]*other.mat[0*4+3],  # i=0,j=3

            self.mat[0*4+0]*other.mat[1*4+0] + self.mat[1*4+0]*other.mat[1*4+1] + self.mat[2*4+0]*other.mat[1*4+2] + self.mat[3*4+0]*other.mat[1*4+3],  # i=1,j=0
            self.mat[0*4+1]*other.mat[1*4+0] + self.mat[1*4+1]*other.mat[1*4+1] + self.mat[2*4+1]*other.mat[1*4+2] + self.mat[3*4+1]*other.mat[1*4+3],  # i=1,j=1
            self.mat[0*4+2]*other.mat[1*4+0] + self.mat[1*4+2]*other.mat[1*4+1] + self.mat[2*4+2]*other.mat[1*4+2] + self.mat[3*4+2]*other.mat[1*4+3],  # i=1,j=2
            self.mat[0*4+3]*other.mat[1*4+0] + self.mat[1*4+3]*other.mat[1*4+1] + self.mat[2*4+3]*other.mat[1*4+2] + self.mat[3*4+3]*other.mat[1*4+3],  # i=1,j=3

            self.mat[0*4+0]*other.mat[2*4+0] + self.mat[1*4+0]*other.mat[2*4+1] + self.mat[2*4+0]*other.mat[2*4+2] + self.mat[3*4+0]*other.mat[2*4+3],  # i=2,j=0
            self.mat[0*4+1]*other.mat[2*4+0] + self.mat[1*4+1]*other.mat[2*4+1] + self.mat[2*4+1]*other.mat[2*4+2] + self.mat[3*4+1]*other.mat[2*4+3],  # i=2,j=1
            self.mat[0*4+2]*other.mat[2*4+0] + self.mat[1*4+2]*other.mat[2*4+1] + self.mat[2*4+2]*other.mat[2*4+2] + self.mat[3*4+2]*other.mat[2*4+3],  # i=2,j=2
            self.mat[0*4+3]*other.mat[2*4+0] + self.mat[1*4+3]*other.mat[2*4+1] + self.mat[2*4+3]*other.mat[2*4+2] + self.mat[3*4+3]*other.mat[2*4+3],  # i=2,j=3

            self.mat[0*4+0]*other.mat[3*4+0] + self.mat[1*4+0]*other.mat[3*4+1] + self.mat[2*4+0]*other.mat[3*4+2] + self.mat[3*4+0]*other.mat[3*4+3],  # i=3,j=0
            self.mat[0*4+1]*other.mat[3*4+0] + self.mat[1*4+1]*other.mat[3*4+1] + self.mat[2*4+1]*other.mat[3*4+2] + self.mat[3*4+1]*other.mat[3*4+3],  # i=3,j=1
            self.mat[0*4+2]*other.mat[3*4+0] + self.mat[1*4+2]*other.mat[3*4+1] + self.mat[2*4+2]*other.mat[3*4+2] + self.mat[3*4+2]*other.mat[3*4+3],  # i=3,j=2
            self.mat[0*4+3]*other.mat[3*4+0] + self.mat[1*4+3]*other.mat[3*4+1] + self.mat[2*4+3]*other.mat[3*4+2] + self.mat[3*4+3]*other.mat[3*4+3],  # i=3,j=3
        ]
        
        return self
        
    def scale(self, x: float, y: float, z: float):
        return self.transform(Matrix44([
            x, 0.0, 0.0, 0.0,
            0.0, y, 0.0, 0.0,
            0.0, 0.0, z, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
    
    def translate(self, x: float, y: float, z: float):
        return self.transform(Matrix44([
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            x, y, z, 1.0
        ]))
    
    def skew_x(self, angle_rad: float):
        return self.transform(Matrix44([
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, math.tan(angle_rad), 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
    
    def skew_y(self, angle_rad: float):
        return self.transform(Matrix44([
            1.0, 0.0, math.tan(angle_rad), 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
    
    def skew_z(self, angle_rad: float):
        return self.transform(Matrix44([
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, math.tan(angle_rad), 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
    
    def rotate_x(self, angle_rad: float):
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        return self.transform(Matrix44([
            1.0, 0.0, 0.0, 0.0,
            0.0, c, s, 0.0,
            0.0, -s, c, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
    
    def rotate_y(self, angle_rad: float):
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        return self.transform(Matrix44([
            c, 0.0, -s, 0.0,
            0.0, 1.0, 0.0, 0.0,
            s, 0.0, c, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
    
    def rotate_z(self, angle_rad: float):
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        return self.transform(Matrix44([
            c, s, 0.0, 0.0,
            -s, c, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]))
    
@dataclasses.dataclass
class Triangle:
    p1: tuple[float, float]
    p2: tuple[float, float]
    p3: tuple[float, float]
    color: tuple[float, float, float, float]

@dataclasses.dataclass
class Viewport:
    height: float = -55.0
    origin: tuple[float, float] = (0.0, 0.0)
    size: tuple[float, float] = (1.0, 1.0)

class Renderer:
    def __init__(self, name: str = "renderer"):
        self.client = minecraft_ipclink.IPCLinkClient(name)
        self.client.runForever(inOtherThread=True)
        self.triangles: list[typing.Optional[Triangle]] = []
        self.viewport = Viewport()
        
        self._entname = "text_display"
        self._tag = "rdt"
        
        self._frame_counter = 0
        self._swap_size = 5
        self._commands = []
        
        self._commandKillAll()
    
    def _makeCounterTag(self, cut: int):
        return f"ct_{cut}"
    
    def _commandAdd(self, parts: list[str]):
        self._commands.append(" ".join(parts))
    
    def _commandAddTextDisplay(self, color: tuple[float, float, float, float], matrix: Matrix44):
        matrix = (
            matrix.copy()
            .translate(0.4, 0.0, 1.0)
            .rotate_x(-math.pi / 2)
            .scale(8.0, 3.635, 1.0)
        )
        
        nbt = {
            "text": json.dumps(" ", ensure_ascii=False),
            "background": _cvtColor(color),
            "Tags": [self._tag, self._makeCounterTag(self._frame_counter)],
            "transformation": list(map(lambda x: float(round(x, 5)), [
                matrix.mat[0], matrix.mat[4], matrix.mat[8], matrix.mat[12],
                matrix.mat[1], matrix.mat[5], matrix.mat[9], matrix.mat[13],
                matrix.mat[2], matrix.mat[6], matrix.mat[10], matrix.mat[14],
                matrix.mat[3], matrix.mat[7], matrix.mat[11], matrix.mat[15]
            ]))
        }
        
        self._commandAdd([
            "summon", self._entname,
            str(float(self.viewport.origin[0])),
            str(float(self.viewport.height)),
            str(float(self.viewport.origin[1])),
            json.dumps(nbt, separators=(',', ':'), ensure_ascii=False)
        ])
        
    def _commandKillAll(self):
        selector = [
            f"type={self._entname}",
            f"tag={self._tag}"
        ]
        
        self._commandAdd(["kill", f"@e[{', '.join(selector)}]"])
    
    def _commandKillOlds(self):
        selector = [
            f"type={self._entname}",
            f"tag={self._tag}",
            *(f"tag=!{self._makeCounterTag(self._frame_counter - i)}" for i in range(self._swap_size + 1))
        ]
        
        self._commandAdd(["kill", f"@e[{', '.join(selector)}]"])
    
    def _commandsClear(self):
        self._commands.clear()
    
    def _commandsRun(self):
        self.client.runCommands(self._commands)
    
    def _updateFrameCounter(self):
        self._frame_counter += 1
    
    def _pointToScreen(self, pt: tuple[float, float]):
        return (pt[0] * self.viewport.size[0], pt[1] * self.viewport.size[1])
    
    def _signedDistToLine(self, lp1: tuple[float, float], lp2: tuple[float, float], p: tuple[float, float]):
        x1, y1 = lp1; x2, y2 = lp2; x3, y3 = p
        vx = x2 - x1; vy = y2 - y1
        wx = x3 - x1; wy = y3 - y1
        cross = vx * wy - vy * wx
        norm2 = vx * vx + vy * vy
        if norm2 == 0.0: return math.hypot(x3 - x1, y3 - y1)
        return cross / math.sqrt(norm2)
    
    def _signedProjection(self, lp1: tuple[float, float], lp2: tuple[float, float], p3: tuple[float, float]):
        vx = lp2[0] - lp1[0]
        vy = lp2[1] - lp1[1]
        wx = p3[0] - lp1[0]
        wy = p3[1] - lp1[1]
        len_v = math.hypot(vx, vy)
        if len_v == 0.0: return 0.0
        return (vx * wx + vy * wy) / len_v
    
    def _sign(self, x: float):
        return 1.0 if x >= 0.0 else -1.0
    
    def _renderGenerateCommands(self):
        layer_delta_y = 0
        
        for tri in self.triangles:
            if tri is None:
                layer_delta_y += 0.0001
                continue
                
            p1 = self._pointToScreen(tri.p1)
            p2 = self._pointToScreen(tri.p2)
            p3 = self._pointToScreen(tri.p3)
            
            p1, p2, p3 = sorted((p1, p2, p3), key=lambda p: p[0])
            if p1[0] != p3[0]:
                cross = (p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])
                if cross > 0.0: p1, p2, p3 = p1, p3, p2
            
            p1_p2_dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            p3_dist = self._signedDistToLine(p1, p2, p3)
            p3_proj = self._signedProjection(p1, p2, p3)
            
            assert p3_dist >= 0.0, "p3_dist must be >= 0.0"
            
            mat = Matrix44()
            mat.translate(p1[1], layer_delta_y, p1[0])
            mat.rotate_y(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
            mat.skew_y(math.atan2(p3_proj, p3_dist))
            mat.scale(p3_dist, 1.0, p1_p2_dist)
            
            self._commandAddTextDisplay(tri.color, mat.copy().scale(0.5, 1.0, 0.5))
            self._commandAddTextDisplay(tri.color, mat.copy().translate(0.0, 0.0, 0.5).skew_y(-math.pi / 4).scale(0.5, 1.0, 0.5))
            self._commandAddTextDisplay(tri.color, mat.copy().translate(0.0, 0.0, 0.5).rotate_y(math.pi / 2).skew_y(math.pi / 4).scale(0.5, 1.0, 0.5))
        
        self._commandKillOlds()
        
    def render(self):
        self._renderGenerateCommands()
        self._commandsRun()
        self._commandsClear()
        self._updateFrameCounter()
    
    def nextLayer(self):
        self.triangles.append(None)

    def addRect(self, position: tuple[float, float], size: tuple[float, float], color: tuple[float, float, float, float]):
        self.triangles.append(Triangle(
            p1 = (position[0], position[1]),
            p2 = (position[0] + size[0], position[1]),
            p3 = (position[0], position[1] + size[1]),
            color = color
        ))
        
        self.triangles.append(Triangle(
            p1 = (position[0] + size[0], position[1]),
            p2 = (position[0] + size[0], position[1] + size[1]),
            p3 = (position[0], position[1] + size[1]),
            color = color
        ))
    
    def addRectCentered(self, position: tuple[float, float], size: tuple[float, float], color: tuple[float, float, float, float]):
        self.addRect((position[0] - size[0] / 2, position[1] - size[1] / 2), size, color)
    
    def addCircle(self, center: tuple[float, float], radius: float, color: tuple[float, float, float, float]):
        segs = 8
        
        for i in range(segs):
            p = i / segs
            np = (i + 1) / segs
            
            cp = math.cos(p * math.pi * 2)
            sp = math.sin(p * math.pi * 2)
            ncp = math.cos(np * math.pi * 2)
            nsp = math.sin(np * math.pi * 2)
            
            self.triangles.append(Triangle(
                p1 = center,
                p2 = (center[0] + cp * radius, center[1] + sp * radius),
                p3 = (center[0] + ncp * radius, center[1] + nsp * radius),
                color = color
            ))
    
    def addRing(self, center: tuple[float, float], radius: float, ringRadius: float, color: tuple[float, float, float, float]):
        segs = 8
        
        for i in range(segs):
            p = i / segs
            np = (i + 1) / segs
            
            cp = math.cos(p * math.pi * 2)
            sp = math.sin(p * math.pi * 2)
            ncp = math.cos(np * math.pi * 2)
            nsp = math.sin(np * math.pi * 2)
            
            p1 = (center[0] + cp * radius, center[1] + sp * radius)
            p2 = (center[0] + ncp * radius, center[1] + nsp * radius)
            p3 = (center[0] + ncp * ringRadius, center[1] + nsp * ringRadius)
            p4 = (center[0] + cp * ringRadius, center[1] + sp * ringRadius)
            
            self.triangles.append(Triangle(
                p1 = p1,
                p2 = p2,
                p3 = p3,
                color = color
            ))
            
            self.triangles.append(Triangle(
                p1 = p1,
                p2 = p3,
                p3 = p4,
                color = color
            ))

if __name__ == "__main__":
    renderer = Renderer()
    renderer._swap_size = 1

    import time

    while True:
        renderer.triangles.clear()
        t = time.perf_counter() * 2
        
        renderer.triangles.append(Triangle(
            p1 = (math.cos(t), math.sin(t)),
            p2 = (math.cos(t + math.pi / 2), math.sin(t + math.pi / 2)),
            p3 = (math.cos(t + math.pi), math.sin(t + math.pi)),
            color = (69 / 255, 161 / 255, 232 / 255, 1.0)
        ))
        
        renderer.nextLayer()
        
        renderer.addRect((0.5, 0.5), (0.1, 0.1), (1.0, 0.0, 0.0, 1.0))
        renderer.nextLayer()
        
        renderer.addCircle((0.5, 0.5), 0.1 + math.sin(t) * 1, (0.0, 1.0, 0.0, 1.0))
        renderer.nextLayer()
        
        renderer.addRing((-0.5, -0.5), 0.1 + math.sin(t) * 1, (0.1 + math.sin(t) * 1) * 0.5, (0.0, 0.0, 1.0, 1.0))

        renderer.render()
        time.sleep(1 / 30)
        