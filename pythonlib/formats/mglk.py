import struct
from dataclasses import dataclass
from pathlib import Path

from ..formats.FileIO import FileIO
from ..utils import comptolib

MAGIC = b"MGLK"


@dataclass
class mglk_file():
    is_compressed: bool
    type: int
    data: bytes


class Mglk():
    def __init__(self) -> None:
        self.unk1 = 0x100
        self.unk2 = 0x7
        self.total_files = 0x0
        self.unk3 = 0x1
        self.opt_files = 0x2
        self.files = []
        self._rsce = b""
        self._rsce_pos = 0
        self._rsce_found = False

    
    @staticmethod
    def from_path(path: Path) -> 'Mglk':
        with FileIO(path) as f:
            if f.read(4) != MAGIC:
                raise ValueError("Not a MGLK file!")
            
            self = Mglk()
            self.unk1 = f.read_uint32()
            self.unk2 = f.read_uint16()
            self.total_files = f.read_uint16()
            self.unk3 = f.read_uint16()
            self.opt_files = f.read_uint16()
            self._rsce_found = 0
            assert self.unk2 == 7, "MGLK unk2 is not 7!"  # version?
            assert self.unk3 == 1, "MGLK unk3 is not 1!"  # version?
            assert f.read_uint32() == 1, "MGLK unk4 is not 1!"  # version?
            assert f.read_uint32() == 0, "MGLK padding_1 is not zero!"  # padding?
            assert f.read_uint32() == 0, "MGLK padding_2 is not zero!"  # padding?
            assert f.read_uint32() == 0, "MGLK padding_3 is not zero!"  # padding?
            self.files = []

            sizes = []
            for _ in range(self.total_files):
                sizes.append(f.read_uint32())

            for i, size in enumerate(sizes):
                data = f.read(size)
                is_compressed = comptolib.is_compressed(data)
                c_type = 0
                if is_compressed:
                    c_type = data[0]
                    data = comptolib.decompress_data(data)

                if len(data) > 8 and data[0:8] == b"TOD1RSCE":
                    self._rsce = data
                    self._rsce_pos = i
                    self._rsce_found += 1

                self.files.append(mglk_file(is_compressed, c_type, data))

            assert self._rsce_found == 1, "MGLK with no rsce or more than one are unsupported!"

        return self
    

    def to_bytes(self):
        out = MAGIC
        out += struct.pack("<I", self.unk1)
        out += struct.pack("<H", self.unk2)
        out += struct.pack("<H", self.total_files)
        out += struct.pack("<H", self.unk3)
        out += struct.pack("<H", self.opt_files)
        out += struct.pack("<I", 1)
        out += struct.pack("<I", 0)
        out += struct.pack("<I", 0)
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
