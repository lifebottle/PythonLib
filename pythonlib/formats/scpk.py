from dataclasses import dataclass
from ..formats.FileIO import FileIO
from ..utils import comptolib

MAGIC = b"SCPK"


@dataclass
class scpk_file():
    is_compressed: bool
    type: int
    data: bytes


class Scpk(FileIO):
    def __init__(self, path="") -> None:
        super().__init__(path, "r+b", "<")
        super().__enter__()
        if self.read(4) != MAGIC:
            raise ValueError("Not an SCPK file!")

        self.unk1 = self.read_uint16()
        self.unk2 = self.read_uint16()
        file_amount = self.read_uint32()
        self.read_uint32()  # padding?
        self.files = []

        sizes = []
        for _ in range(file_amount):
            sizes.append(self.read_uint32())

        for size in sizes:
            data = self.read(size)
            is_compressed = comptolib.is_compressed(data)
            c_type = 0
            if is_compressed:
                c_type = data[0]
                data = comptolib.decompress_data(data)

            if len(data) > 8 and data[0:8] == b"THEIRSCE":
                self.rsce = data

            self.files.append(scpk_file(is_compressed, c_type, data))

    def __getitem__(self, item):
        return self.files[item]

    def __len__(self):
        return len(self.files)
