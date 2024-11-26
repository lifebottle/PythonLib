from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Generator, Union

from ..FileIO import FileIO
from .theirsce_funcs import SYSCALL_NAMES
from .theirsce_instructions import (
    AluOperation,
    BranchType,
    InstructionType,
    ReferenceScope,
    TheirsceAcquireInstruction,
    TheirsceAluInstruction,
    TheirsceBaseInstruction,
    TheirsceBranchInstruction,
    TheirsceBreakInstruction,
    TheirsceLocalCallInstruction,
    TheirscePushInstruction,
    TheirsceReferenceInstruction,
    TheirsceReturnInstruction,
    TheirsceSpecialReferenceInstruction,
    TheirsceStringInstruction,
    TheirsceSyscallInstruction,
    VariableType,
)

# I followed other project when making this class
# not sure how if it's the best approach

SECTION_AMOUNT = 6 

@dataclass
class subsection:
    unk1: int
    unk2: int
    off:  int

@dataclass
class function:
    arguments: list
    body:  list
    visited: bool = False


class Theirsce(FileIO):
    def __init__(self, path: Union[Path, str, BytesIO, bytes] ="") -> None:
        super().__init__(path, "r+b", "<")
        super().__enter__()
        self.magic = self.read(8)

        if self.magic != b"THEIRSCE":
            raise ValueError("Not a THEIRSCE file!")

        self.code_offset    = self.read_uint32()
        self.strings_offset = self.read_uint32()
        self.unk_field      = self.read_uint32()

        self.frame_offset = self.read_uint16()
        self.entry_offset = self.read_uint16()

        self.sections: list[list[subsection]] = []
        # section_stop = self.readUShort(); self.seek(-2, 1)
        #section_amount = (section_stop - 0x18) // 2

        for _ in range(SECTION_AMOUNT):
            pos = self.tell() + 2
            self.seek(self.read_uint16())

            subsections: list[subsection] = []
            for _ in range(self.read_uint16()):
                sub = subsection(self.read_uint16(), self.read_uint16(), self.read_uint16() + self.code_offset)
                subsections.append(sub)
            self.sections.append(subsections)
            self.seek(pos)

        self.functions = self.get_functions()
    
    def __enter__(self):
        return super().__enter__()
    
    def __exit__(self, exc_type, exc_value, traceback):
        return super().__exit__(exc_type, exc_value, traceback)
        
    def walk_code(self, start=None, end=None) -> Generator[TheirsceBaseInstruction, None, None]:
        start = self.code_offset if start is None else start
        end = self.strings_offset if end is None else end

        self.seek(start)

        while self.tell() < end:
            opcode = self.read_opcode()
            pos = self.tell()
            yield opcode
            self.seek(pos)

    @staticmethod
    def read_tag_bytes(src) -> bytes:
        data = b""
        
        while True:
            c = src.read(1)
            if c == b"\x80":
                data += c
                break

            data += c
            opcode = data[-1]
            
            if opcode < 0x80: 
                if opcode & 8 != 0: 
                    data += src.read(2)
                else:
                    data += src.read(1)
                    
            elif opcode < 0xC0:
                continue

            elif opcode < 0xE0:
                size_mask = (opcode >> 3) & 3

                if size_mask == 1: data += src.read(1)
                elif size_mask == 2: data += src.read(2)
                elif size_mask == 3: data += src.read(4)

            elif opcode < 0xF0:
                data += src.read(1)
            
            elif opcode < 0xF8:
                if (0xF2 <= opcode < 0xF5) or opcode == 0xF7:
                    data += src.read(2)
                elif opcode == 0xF5:
                    data += src.read(4)
                elif opcode == 0xF6:
                    data += src.read(1)
                    for _ in range(data[-1]):
                        cc = src.read_uint8()
                        data += cc
                        if cc & 8 != 0:
                            data += src.read(2) 
                        else:
                            data += src.read(3)
            
            elif opcode < 0xFC:
                data += src.read(2)
            
            elif opcode == 0xFE:
                continue

        return data

    def get_functions(self):
        funs: dict[int, function] = {}
        ops = list(self.walk_code())

        bd = []
        fn_st = ops[0].position; ops.pop(0)
        for val in ops:
            if val.type == InstructionType.BREAK:
                if bd[0].type == InstructionType.ACQUIRE:
                    funs[fn_st] = function(bd[0].params, bd)
                    bd.pop(0)
                else:
                    funs[fn_st] = function([], bd)
                fn_st = val.position
                bd = []
            else:
                bd.append(val)

        if bd[0].type == InstructionType.ACQUIRE:
            funs[fn_st] = function(bd[0].params, bd)
            bd.pop(0)
        else:
            funs[fn_st] = function([], bd)

        return funs
    
    def reset_seen_functions(self):
        for fun in self.functions.values():
            fun.visited = False

    def read_opcode(self) -> TheirsceBaseInstruction:
        pos = self.tell()
        opcode = self.read_uint8()

        # Reference Block
        if opcode < 0x80: 
            var_type = (opcode >> 4) & 7
            shift = 0

            #id = mask
            if var_type == 0: # bitfields
                value = self.read_uint8()
                if opcode & 8 == 0:
                    next_byte = opcode & 3
                    pass
                else:
                    next_byte = self.read_uint8()
                    pass
                shift = (value & 7) #<< 3
                value = ((( value | (next_byte << 8)) >> 3) & 0xFF)
            else:
                value = self.read_uint8()
                top = 1
                if opcode & 8 != 0:
                    top = 2
                    next_byte = self.read_uint8()
                    value = ( ((next_byte & 0xFF) << 8) | (value & 0xFF))
                value = ((opcode & 3) << (8 * top)) | value

            # scope
            if opcode & 4 == 0:
                if value < 0x400:
                    scope = ReferenceScope.GLOBAL
                else:
                    scope = ReferenceScope.FILE
                    value -= 0x400
            else:
                scope = ReferenceScope.LOCAL

            return TheirsceReferenceInstruction(ref_type=VariableType(var_type), scope=scope, offset=value, shift=shift, position=pos)

        # ALU operations
        elif opcode < 0xC0:
            return TheirsceAluInstruction(operation = AluOperation(opcode & 0x3F), position=pos)

        # PUSH block, the amount of bytes depend on encoding
        elif opcode < 0xE0:
            size_mask = (opcode >> 3) & 3
            signed = opcode & 4 != 0
            top = opcode & 7

            if size_mask == 0:
                value = 0xFFFFFF00 | (top | 0xF8) if signed else top
            elif size_mask == 1:
                value = top << 8 | self.read_uint8()
                value = value | 0xFFFF0000 | 0xF800 if signed else value
            elif size_mask == 2:
                value = top << 16 | self.read_uint16()
                value = value | 0xFF000000 | 0xF80000 if signed else value
            else: #if size_mask == 3:
                value = self.read_uint32()
            
            # to signed
            value = value | (-(value & 0x80000000))

            return TheirscePushInstruction(value=value, position=pos)

        # CALL block, available commands are at 0x1e5300
        # first entry is number of parameters then function
        elif opcode < 0xF0:
            index = ((opcode & 0xF) << 8) | self.read_uint8()
            return TheirsceSyscallInstruction(function_index=index, function_name=SYSCALL_NAMES[index], position=pos)

        # Flow related block
        elif opcode < 0xF8:
            if opcode == 0xF0:
                return TheirsceReturnInstruction(is_void=True, position=pos)
            elif opcode == 0xF1:
                return TheirsceReturnInstruction(is_void=False, position=pos)
            
            # Need to be offsetted to start of code
            elif opcode >= 0xF2 and opcode < 0xF5:
                target = self.code_offset + self.read_uint16()
                return TheirsceBranchInstruction(branch_type=BranchType(opcode - 0xF2), destination=target, position=pos)
            elif opcode == 0xF5:
                target = self.code_offset + self.read_uint16()
                reserve = self.read_uint16()
                return TheirsceLocalCallInstruction(destination=target, reserve=reserve, position=pos)
            
            # ?
            elif opcode == 0xF6:
                variables = self.read_uint8() 
                params = []
                for _ in range(variables):
                    if self.read_uint8() & 8 != 0:
                        params.append(self.read_uint16())
                    else:
                        params.append(self.read_uint8())
            
                return TheirsceAcquireInstruction(params=params,variables=variables, position=pos)

            else: # if opcode == 0xF7:
                param = self.read_uint16() # Type?
                return TheirsceBreakInstruction(param=param, position=pos)
        
        # Get string
        elif opcode < 0xFC:
            value = ((opcode & 3) << 16) | self.read_uint16()
            return TheirsceStringInstruction(offset=value,text="", position=pos)

        # ?
        else: # if opcode == 0xFE:
            return TheirsceSpecialReferenceInstruction(position=pos)
        
        # Impossible
        # else:
        #     raise ValueError(f"INVALID OPCODE 0x{opcode:2X}")
    
# if __name__ == "__main__":
#     with Theirsce("./10233d.theirsce") as f:
#         for op in f.walk_code():
#             if op.type == InstructionType.ACQUIRE:
#                 print(op)