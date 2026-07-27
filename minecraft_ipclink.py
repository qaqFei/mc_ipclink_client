import ctypes
import typing
import threading
import json
import random
import queue

class ShmSocket:
    lib = ctypes.CDLL("./shm_socket.dll")
    callback_refs: dict = {}
    
    @staticmethod
    def createClient(name: str, callback: typing.Callable[[bytes], None]) -> int:
        ShmSocket.lib.createClient.argtypes = (ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_bool))
        ShmSocket.lib.createClient.restype = ctypes.c_void_p
        
        success = ctypes.c_bool()
        funcptr = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64)(lambda _, ptr, size: callback(ctypes.string_at(ptr, size)))
        
        client = ShmSocket.lib.createClient(
            name.encode("utf-8"),
            funcptr,
            ctypes.c_void_p(0),
            ctypes.byref(success)
        )
        
        if not success.value:
            raise Exception("Failed to create client")
        
        ShmSocket.callback_refs[client] = funcptr
        return client
    
    @staticmethod
    def clientGetShutdown(client: int) -> bool:
        ShmSocket.lib.clientGetShutdown.argtypes = (ctypes.c_void_p, )
        ShmSocket.lib.clientGetShutdown.restype = ctypes.c_bool

        return ShmSocket.lib.clientGetShutdown(client)
    
    @staticmethod
    def clientSend(client: int, data: bytes) -> None:
        ShmSocket.lib.clientSend.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64)
        ShmSocket.lib.clientSend.restype = None

        ShmSocket.lib.clientSend(client, data, len(data))
    
    @staticmethod
    def clientRecv(client: int) -> None:
        ShmSocket.lib.clientRecv.argtypes = (ctypes.c_void_p, )
        ShmSocket.lib.clientRecv.restype = None

        ShmSocket.lib.clientRecv(client)
    
    @staticmethod
    def destroyClient(client: int) -> None:
        ShmSocket.lib.destroyClient.argtypes = (ctypes.c_void_p, )
        ShmSocket.lib.destroyClient.restype = None

        ShmSocket.lib.destroyClient(client)
        ShmSocket.callback_refs.pop(client)
    
    @staticmethod
    def setBusywait(value: bool) -> None:
        ShmSocket.lib.setBusywait.argtypes = (ctypes.c_bool, )
        ShmSocket.lib.setBusywait.restype = None

        ShmSocket.lib.setBusywait(value)

def makeIPCServerRealName(name: str) -> str:
    return "/minecraft_ipclink_" + name

class IPCLinkClient:
    def __init__(self, name: str, *, buffer_size: int = 16):
        self._client = ShmSocket.createClient(makeIPCServerRealName(name), self._recv)
        self._callbacks = {}
        self._send_queue: queue.Queue[typing.Optional[bytes]] = queue.Queue(maxsize=buffer_size)
        self._send_thread = threading.Thread(target=self._sender, daemon=True)
        self._send_thread.start()
    
    def _recv(self, data: bytes):
        data = json.loads(data.decode("utf-8"))
        seq = data["seq"]
        
        def check_seq(target: int, msg: str):
            if seq == target:
                raise Exception("invalid packet was sent: " + msg)

        check_seq(0, "json syntax error")
        check_seq(1, "json structure is wrong")
        check_seq(2, "undefined packet type")
        check_seq(3, "invalid packet seq")
        
        callback = self._callbacks[seq]
        if callback is not None: callback(data["data"])
        
        self._callbacks.pop(seq)
    
    def _sender(self):
        while True:
            data = self._send_queue.get()
            if data is None: break
            
            ShmSocket.clientSend(self._client, data)
    
    def _send(self, data: bytes):
        if len(data) > 2147483647:
            raise Exception("data is too large")
        
        self._send_queue.put(data)
    
    def _sendPacket(self, type: str, data: typing.Any, callback: typing.Optional[typing.Callable[[typing.Any], None]] = None):
        seq = random.randint(512, 2147483647)
        self._callbacks[seq] = callback
        
        self._send(json.dumps({
            "type": type,
            "data": data,
            "seq": seq
        }, ensure_ascii=False).encode("utf-8"))
    
    def runCommand(self, command: str, callback: typing.Optional[typing.Callable[[int], None]] = None):
        self._sendPacket("runCommand", command, callback)
    
    def runCommands(self, commands: list[str], callback: typing.Optional[typing.Callable[[list[int]], None]] = None):
        self._sendPacket("runCommands", commands, callback)
    
    def runForever(self, inOtherThread: bool = False):
        if inOtherThread:
            threading.Thread(target=self.runForever, daemon=True).start()
            return
        
        while not ShmSocket.clientGetShutdown(self._client):
            ShmSocket.clientRecv(self._client)
        
    def __del__(self):
        try:
            self._send_queue.put(None)
            self._send_thread.join()
            ShmSocket.destroyClient(self._client)
        except Exception:
            pass

if __name__ == "__main__":
    client = IPCLinkClient("test")
    client.runForever(inOtherThread=True)
    
    while True:
        msg = input(">> ")
        client.runCommand(msg)
