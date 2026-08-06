import typing
import json
import threading

import openai
import openai.types.chat

import minecraft_ipclink

class McpFunctions:
    def __init__(self, name: str):
        self._client = minecraft_ipclink.IPCLinkClient(name)
        self._client.runForever(inOtherThread=True)
    
    def _dumpNbt(self, nbt: dict):
        return json.dumps(nbt, ensure_ascii=False, separators=(",", ":"))

    def _dumpBlock(self, state: str, nbt: typing.Optional[dict] = None):
        return f"{state}{self._dumpNbt(nbt) if nbt is not None else ''}"
    
    def _callClient(self, func: typing.Callable, *args):
        result, event = None, threading.Event()
        
        def callback(r: dict):
            nonlocal result
            result = r
            event.set()
        
        func(*args, callback)
        event.wait()
        return result
    
    def getBlockInfo(self, x: int, y: int, z: int) -> dict:
        return self._callClient(self._client.getBlockInfo, "overworld", x, y, z)
    
    def setBlock(self, x: int, y: int, z: int, blockState: str, blockNbt: typing.Optional[dict] = None) -> bool:
        cmd = f"setblock {x} {y} {z} {self._dumpBlock(blockState, blockNbt)} destroy"
        return self._callClient(self._client.runCommand, cmd) > 0
    
    def fillBlocks(self, p1: tuple[int, int, int], p2: tuple[int, int, int], blockState: str, blockNbt: typing.Optional[dict] = None, isOutline: bool = False) -> bool:
        cmd = f"fill {p1[0]} {p1[1]} {p1[2]} {p2[0]} {p2[1]} {p2[2]} {self._dumpBlock(blockState, blockNbt)} {'outline' if isOutline else 'destroy'}"
        return self._callClient(self._client.runCommand, cmd) > 0
    
    def say(self, text: str) -> bool:
        return self._callClient(self._client.runCommand, f"say {text}") > 0

class MinecraftAgent:
    def __init__(self, mcpFuncs: McpFunctions, baseUrl: str, apiKey: str, modelConfig: dict):
        self.client = openai.OpenAI(api_key=apiKey, base_url=baseUrl)
        self.modelConfig = modelConfig
        self.mcpFuncs = mcpFuncs
        self.conversationHistory = []
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "getBlockInfo",
                    "description": """\
获取指定位置的方块信息
返回值示例:

>> getBlockInfo(1, -60, -4)
{'blockState': {'Properties': {'waterlogged': 'false', 'type': 'single', 'facing': 'west'}, 'Name': 'minecraft:chest'}, 'nbt': {'Items': [{'Slot': 0, 'id': 'minecraft:grass_block', 'Count': 1}]}}

表示在 -1, -60, -4 处, 有一个面朝西方不含水的单个箱子, 里面的第一个槽位装着一个草方块
""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "x 坐标"},
                            "y": {"type": "integer", "description": "y 坐标"},
                            "z": {"type": "integer", "description": "z 坐标"}
                        },
                        "required": ["x", "y", "z"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "setBlock",
                    "description": """\
设置指定位置的方块
返回值表示是否成功

示例:

在 0 -60 0 处, 创建一个含水的空箱子
>> setBlock(0, -60, 0, "minecraft:chest[waterlogged=true]")

在 5 -60 5 处, 创建一个装有 64 个金合欢木门作为燃料的熔炉
>> setBlock(5, -60, 5, "minecraft:blast_furnace", {
    "Items": [
        {
            "Slot": 1,
            "Count": 64,
            "id": "minecraft:acacia_door"
        }
    ]
})
""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "x 坐标"},
                            "y": {"type": "integer", "description": "y 坐标"},
                            "z": {"type": "integer", "description": "z 坐标"},
                            "blockState": {"type": "string", "description": "方块状态，如 'minecraft:stone' 或 'minecraft:oak_log[axis=y]'"},
                            "blockNbt": {"type": "object", "description": "方块的 Nbt 数据 (可选)"}
                        },
                        "required": ["x", "y", "z", "blockState"]
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fillBlocks",
                    "description": """\
填充指定区域的方块
返回值表示是否成功

示例:

在 0 -60 0 到 5 -60 5 之间, 创建一个石头平台
>> fillBlocks((0, -60, 0), (5, -60, 5), "minecraft:stone")

在 0 -60 0 到 5 -55 5 之间, 创建一个 6x6x6 的开启的面朝北方橡树栅栏门, 使用描边
>> fillBlocks((0, -60, 0), (5, -55, 5), "minecraft:oak_fence_gate[open=true,facing=north]", isOutline=True)

nbt 数据与 setBlock 相同, 这里不作演示
""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "p1": {
                                "type": "array",
                                "description": "起始坐标 [x, y, z]",
                                "items": {"type": "integer"},
                                "minItems": 3, "maxItems": 3
                            },
                            "p2": {
                                "type": "array", 
                                "description": "结束坐标 [x, y, z]",
                                "items": {"type": "integer"},
                                "minItems": 3, "maxItems": 3
                            },
                            "blockState": {"type": "string", "description": "方块状态"},
                            "blockNbt": {"type": "object", "description": "Nbt 数据 (可选)"},
                            "isOutline": {"type": "boolean", "description": "是否只填充边框, 默认为 False"}
                        },
                        "required": ["p1", "p2", "blockState"]
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "say",
                    "description": "在游戏中发送消息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "要发送的消息"}
                        },
                        "required": ["text"]
                    }
                }
            }
        ]

    def _execute(self, funcName: str, args: dict):
        if funcName == "getBlockInfo": return self.mcpFuncs.getBlockInfo(**args)
        elif funcName == "setBlock": return self.mcpFuncs.setBlock(**args)
        elif funcName == "fillBlocks": return self.mcpFuncs.fillBlocks(**args)
        elif funcName == "say": return self.mcpFuncs.say(**args)
        else: raise ValueError(f"Unknown function: {funcName}")
    
    def chat(self):
        if not self.conversationHistory:
            self.conversationHistory.append({
                "role": "system",
                "content": """\
你是一个专业的 Minecraft 建造助手, 拥有在 Minecraft Java Edition 1.20.1 世界中操作方块的能力.

## 工作模式
1. **思考阶段** (用户不可见): 在内部仔细规划建造方案, 分析需求, 计算坐标, 选择合适的工具
2. **执行阶段**: 使用工具执行建造操作
3. **反馈阶段**: 向用户简洁明了地报告完成情况

## 核心能力
你可以使用以下工具:
1. **getBlockInfo** - 查询任意位置的方块信息 (类型, 状态, NBT数据)
2. **setBlock** - 在指定位置放置单个方块
3. **fillBlocks** - 批量填充区域, 大幅提高建造效率
4. **say** - 在游戏中向玩家发送消息

## 注意事项
1. 注意一些特殊方块的放置, 例如门, 床等, 使用 half=lower, half=upper 等属性
2. 注意区分地板与家具的 y 坐标, 避免将家具嵌入地板

现在, 请开始帮助玩家完成Minecraft建造任务!
"""
            })
        
        self.conversationHistory.append({
            "role": "user",
            "content": input(">> ")
        })
        
        while True:
            response: openai.types.chat.ChatCompletion = self.client.chat.completions.create(
                messages = self.conversationHistory,
                tools = self.tools,
                tool_choice = "auto",
                extra_body = {
                    "thinking": {
                        "type": "disabled"
                    }
                },
                **self.modelConfig
            )
            
            assistantMessage = response.choices[0].message
            
            print(assistantMessage.content)
            
            if not assistantMessage.tool_calls:
                self.conversationHistory.append({
                    "role": "assistant",
                    "content": assistantMessage.content or ""
                })
                
                return assistantMessage.content or "Task completed"
            
            self.conversationHistory.append({
                "role": "assistant",
                "content": assistantMessage.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments
                        }
                    }
                    for call in assistantMessage.tool_calls
                ]
            })
            
            for call in assistantMessage.tool_calls:
                arguments = json.loads(call.function.arguments)
                
                print(f"Executing function: {call.function.name} with arguments: {arguments}")
                
                result = self._execute(call.function.name, arguments)
                resultStr = json.dumps(result, ensure_ascii=False)
                self.conversationHistory.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": resultStr
                })
    
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", type=str, required=True)
    parser.add_argument("--api-key", type=str, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--ipclink-name", type=str, default="agent")
    args = parser.parse_args()
    
    agent = MinecraftAgent(
        mcpFuncs = McpFunctions(args.ipclink_name),
        baseUrl = args.base_url,
        apiKey = args.api_key,
        modelConfig = {
            "model": args.model,
            "temperature": 0.7
        }
    )

    while True:
        agent.chat()
