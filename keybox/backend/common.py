import struct


class BaseScryptParams:

    DEFAULT_MEM_COST = 14  # log2 KiB, 2^(N+10) bytes
    DEFAULT_TIME_COST = 19  # log2, 2^N iterations

    def __init__(self, mem_cost: int, time_cost: int):
        self.mem_cost = mem_cost  # log2
        self.time_cost = time_cost  # log2

    def encode(self) -> bytes:
        return struct.pack('BB', self.mem_cost, self.time_cost)

    def decode(self, raw: bytes):
        self.mem_cost, self.time_cost = struct.unpack('BB', raw)


class BaseArgon2Params:

    DEFAULT_MEM_COST = 16  # 16 MiB, log2 KiB, 2^(N+10) bytes
    DEFAULT_TIME_COST = 5  # N iterations

    def __init__(self, mem_cost: int, time_cost: int, threads: int, version: int):
        self.mem_cost = mem_cost  # log2
        self.time_cost = time_cost
        self.threads = threads
        self.version = version

    def encode(self) -> bytes:
        return struct.pack('BBBB', self.version, self.mem_cost, self.time_cost, self.threads)

    def decode(self, raw: bytes):
        self.version, self.mem_cost, self.time_cost, self.threads = struct.unpack('BBBB', raw)
