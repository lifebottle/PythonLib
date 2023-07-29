from dataclasses import dataclass
import struct
from typing import Optional
from ..formats.FileIO import FileIO
from ..utils import comptolib


@dataclass
class pak_file():
    is_compressed: bool
    type: int
    data: bytes


class Pak():
    def __init__(self) -> None:
        self.type = -1
        self.align = False
        self.files = []

    
    @staticmethod
    def from_path(path, type) -> 'Pak':
        with FileIO(path) as f:
            self = Pak()
            # if type == -1:
            #     type = Pak.get_pak_type(f)

            file_amount = f.read_uint32()
            self.files = []
            blobs: list[bytes] = []
            offsets: list[int] = []
            sizes: list[int] = []  

            # Pak0
            if type == 0:
                for _ in range(file_amount):
                    sizes.append(f.read_uint32())
                
                for size in sizes:
                    blobs.append(f.read(size))

            # Pak1
            elif type == 1:
                for _ in range(file_amount):
                    offsets.append(f.read_uint32())
                    sizes.append(f.read_uint32())

                for offset, size in zip(offsets, sizes):
                    f.seek(offset)
                    blobs.append(f.read(size))
            # Pak3
            elif type == 3:
                for _ in range(file_amount):
                    offsets.append(f.read_uint32())
                f.seek(0, 2)
                offsets.append(f.tell())
                for i, j in zip(offsets[::1], offsets[1::1]):
                    sizes.append(j - i)
                for offset, size in zip(offsets, sizes):
                    f.seek(offset)
                    blobs.append(f.read(size))
        
            for off in offsets:
                if off % 0x10 == 0:
                    self.align = True
                break

        for blob in blobs:
            is_compressed = comptolib.is_compressed(blob)
            c_type = 0
            if is_compressed:
                c_type = blob[0]
                blob = comptolib.decompress_data(blob)

            self.files.append(pak_file(is_compressed, c_type, blob))

        return self
    
    @staticmethod
    def get_pak_type(data: bytes) -> Optional[int]:
        is_aligned = False
        
        data_size = len(data)
        if data_size < 0x8: return None
    
        files = struct.unpack("<I", data[:4])[0]
        first_entry = struct.unpack("<I", data[4:8])[0]
    
        # Expectations
        pak1_header_size = 4 + (files * 8)
        pak3_header_size = 4 + (files * 4)
    
        # Check for alignment
        if first_entry % 0x10 == 0:
            is_aligned = True
        
        if pak1_header_size % 0x10 != 0:
            pak1_check = pak1_header_size + (0x10 - (pak1_header_size % 0x10))
        else:
            pak1_check = pak1_header_size
    
        # First test pak0 
        # (pak0 can't be aligned, so header size 
        # would be the same as unaligned pak3)
        if len(data) > pak3_header_size:
            calculated_size = 0
            for size in struct.unpack(f"<{files}I", data[4 : (files + 1) * 4]):
                calculated_size += size
            if calculated_size == len(data) - pak3_header_size:
                return 0
    
        # Test for pak1
        if is_aligned:
            if pak1_check == first_entry:
                return 1
        elif pak1_header_size == first_entry:
                return 1
        
        #Test for pak3
        previous = 0
        for offset in struct.unpack(f"<{files}I", data[4: (files+1)*4]):

            if offset > previous and offset >= pak3_header_size:
                previous = offset
            else:
                return None
        
        last_offset = (4*(files+1))+8
        if data[last_offset : first_entry] == b'\x00' * (first_entry - last_offset):
            return 3
        return None
    

    def to_bytes(self, type=-1) -> bytes:
        
        compose_mode = type if type != -1 else self.type
        if compose_mode == -1:
            raise ValueError("Trying to compose an invalid PAK type")
        
        # Collect blobs
        blobs = []
        for blob in self.files:
            if blob.is_compressed:
                blobs.append(comptolib.compress_data(blob.data, version=blob.type))
            else:
                blobs.append(blob.data)

        # Compose
        out = struct.pack("<I", len(self.files))
        
        # Pak0
        if compose_mode == 0:
            for blob in blobs:
                out += struct.pack("<I", len(blob))
        # Pak1
        elif compose_mode == 1:
            offset = 4 + (8 * len(blobs))
            sizes = [0] + list([len(x) for x in blobs])
            if self.align:
                offset = offset + (0x10 - (offset % 0x10))

            for i, j in zip(sizes[::1], sizes[1::1]):
                if self.align:
                    i = i + (0x10 - (i % 0x10))
                struct.pack("<I", offset + i)
                struct.pack("<I", j)
                offset += i
        # Pak3
        elif compose_mode == 3:
            offset = 4 + (4 * len(blobs))
            if self.align:
                offset = offset + (0x10 - (offset % 0x10))

            cur = offset
            for blob in blobs:
                out += struct.pack("<I", cur)
                cur += len(blob)
                if self.align:
                    cur += (0x10 - (cur % 0x10))

        # add files
        for blob in blobs:
            if self.align:
                out += b"\x00" * (0x10 - (len(out) % 0x10))
            out += blob

        return out
    

    def __getitem__(self, item):
        return self.files[item]

    def __len__(self):
        return len(self.files)
