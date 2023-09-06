import struct
from dataclasses import dataclass
from pathlib import Path

from ..formats.FileIO import FileIO
from ..utils import comptolib

MAGIC = b"SCPK"


@dataclass
class scpk_file():
    is_compressed: bool
    type: int
    data: bytes


class Scpk():
    def __init__(self) -> None:
        self.unk1 = 0
        self.unk2 = 0
        self.files = []
        self._rsce = b""
        self._rsce_pos = 0

    
    @staticmethod
    def from_path(path: Path) -> 'Scpk':
        with FileIO(path) as f:
            if f.read(4) != MAGIC:
                raise ValueError("Not an SCPK file!")
            
            self = Scpk()
            self.unk1 = f.read_uint16()
            self.unk2 = f.read_uint16()
            file_amount = f.read_uint32()
            assert f.read_uint32() == 0, "scpk padding is not zero!"  # padding?
            self.files = []

            sizes = []
            for _ in range(file_amount):
                sizes.append(f.read_uint32())

            for i, size in enumerate(sizes):
                data = f.read(size)
                is_compressed = comptolib.is_compressed(data)
                c_type = 0
                if is_compressed:
                    c_type = data[0]
                    data = comptolib.decompress_data(data)

                if len(data) > 8 and data[0:8] == b"THEIRSCE":
                    self._rsce = data
                    self._rsce_pos = i

                self.files.append(scpk_file(is_compressed, c_type, data))

        return self
    

    def to_bytes(self):
        out = MAGIC
        out += struct.pack("<H", self.unk1)
        out += struct.pack("<H", self.unk2)
        out += struct.pack("<I", len(self.files))
        out += struct.pack("<I", 0)

        blobs = []
        for blob in self.files:
            if blob.is_compressed:
                blobs.append(comptolib.compress_data(blob.data, version=blob.type))
            else:
                blobs.append(blob.data)
        
        # add sizes
        for l in [len(x) for x in blobs]:
            out += struct.pack("<I", l)

        # add files
        for blob in blobs:
            out += blob

        return out
    

    @property
    def rsce(self):
        return self._rsce
    
    @rsce.setter
    def rsce(self, value):
        self._rsce = value
        self.files[self._rsce_pos].data = value


    def __getitem__(self, item):
        return self.files[item]

    def __len__(self):
        return len(self.files)
