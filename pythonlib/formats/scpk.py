import struct
from dataclasses import dataclass
from pathlib import Path

from ..formats.FileIO import FileIO
from ..formats.pak import Pak
from ..utils import comptolib

MAGIC = b"SCPK"

MAP_FLAG = 0x1
CHR_FLAG = 0x2
SCE_FLAG = 0x4
UNK_FLAG = 0x8


@dataclass
class scpk_file:
    is_compressed: bool
    type: int
    data: bytes


class Scpk:
    def __init__(self) -> None:
        self.map: bytes = b""
        self._map_comp_type = 0
        self.chars: dict[int, Pak] = dict()
        self.char_ids: list[int] = list()
        self.rsce: bytes = b""
        self._rsce_comp_type = 0
        self.unk_file: bytes = b""

        self.version = 1

    @staticmethod
    def from_path(path: Path) -> "Scpk":
        with FileIO(path) as f:
            if f.read(4) != MAGIC:
                raise ValueError("Not an SCPK file!")

            self = Scpk()
            self.version = f.read_uint16()
            flags = f.read_uint16()
            file_amount = f.read_uint32()

            # It's not checked by the game
            assert self.version == 1, "scpk version is not 1!"
            assert f.read_uint32() == 0, "scpk padding is not zero!"  # padding?

            sizes = []
            for _ in range(file_amount):
                sizes.append(f.read_uint32())

            cursor = f.tell()

            if flags & MAP_FLAG:
                size = sizes.pop(0)
                self.map = f.read_at(cursor, size)
                self._map_comp_type = self.map[0]
                self.map = comptolib.decompress_data(self.map)
                cursor += size

            if flags & CHR_FLAG:
                f.seek(cursor)
                total_chars = f.read_uint16()
                for _ in range(total_chars):
                    self.char_ids.append(f.read_uint16())
                cursor += sizes.pop(0)

                for id in self.char_ids:
                    size = sizes.pop(0)
                    self.chars[id] = Pak.from_path(f.read_at(cursor, size), 1)
                    cursor += size

            if flags & SCE_FLAG:
                size = sizes.pop(0)
                self.rsce = f.read_at(cursor, size)
                self._rsce_comp_type = self.rsce[0]
                self.rsce = comptolib.decompress_data(self.rsce)
                cursor += size

            if flags & UNK_FLAG:
                size = sizes.pop(0)
                assert size == 4
                self.unk_file = f.read_at(cursor, 1)
                cursor += size

        return self

    def to_bytes(self) -> bytes:
        out = MAGIC
        out += struct.pack("<H", self.version)
        out += struct.pack("<H", self.get_flags())
        out += struct.pack("<I", self.get_total_files())
        out += struct.pack("<I", 0)

        blobs = []

        if self.map:
            blob = comptolib.compress_data(self.map, version=self._map_comp_type)
            blobs.append(_pad_blob(blob, 4, b"#"))

        if self.chars:
            blob = struct.pack("<H", len(self.chars))

            for id in self.chars.keys():
                blob += struct.pack("<H", id)

            blobs.append(_pad_blob(blob, 4, b"#"))

            for chr in self.chars.values():
                blobs.append(_pad_blob(chr.to_bytes(), 4, b"\x00"))

        if self.rsce:
            blob = comptolib.compress_data(self.rsce, version=self._rsce_comp_type)
            blobs.append(_pad_blob(blob, 4, b"#"))

        if self.unk_file:
            blobs.append(_pad_blob(self.unk_file, 4, b"#"))

        # add sizes
        for size in [len(x) for x in blobs]:
            out += struct.pack("<I", size)

        # add files
        for blob in blobs:
            out += blob

        return out

    def get_total_files(self) -> int:
        total_files = 0
        if self.map:
            total_files += 1
        if self.chars:
            total_files += 1
            total_files += len(self.chars)
        if self.rsce:
            total_files += 1
        if self.unk_file:
            total_files += 1

        return total_files

    def get_flags(self) -> int:
        total_files = 0
        if self.map:
            total_files |= MAP_FLAG
        if self.chars:
            total_files |= CHR_FLAG
        if self.rsce:
            total_files |= SCE_FLAG
        if self.unk_file:
            total_files |= UNK_FLAG

        return total_files


def _pad_blob(blob: bytes, pad_to: int, pad_char: bytes) -> bytes:
    if (len(blob) % pad_to) != 0:
        blob = blob + (pad_char * (pad_to - ((len(blob)) % pad_to)))
    return blob
