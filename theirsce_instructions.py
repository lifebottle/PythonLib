from dataclasses import dataclass, field
from enum import Enum

class VariableType(Enum):
    BIT   = 0
    BYTE  = 1
    SHORT = 2
    INT   = 3
    PTR   = 4


class ReferenceScope(Enum):
    LOCAL  = 0
    FILE   = 1
    GLOBAL = 2


class BranchType(Enum):
    UNCONDITIONAL = 0
    NOT_EQUALS    = 1
    EQUALS        = 2


class InstructionType(Enum):
    ALU        = 0
    PUSH       = 1
    SYSCALL    = 2
    BRANCH     = 3
    LOCAL_CALL = 4
    RETURN     = 5
    ACQUIRE    = 6
    BREAK      = 7
    STRING     = 8
    REFERENCE  = 9
    SP_REF     = 10


class AluOperation(Enum):
    # UNARY
    SWITCH_POP          = 0
    POST_INCREMENT      = 1
    POST_DECREMENT      = 2
    PRE_INCREMENT       = 3
    PRE_DECREMENT       = 4
    ARITHMETIC_NEGATION = 5
    BITWISE_NOT         = 6
    LOGICAL_NOT         = 7

    # BINARY
    INDEX_ARRAY                    = 8
    SUBSCRIPT                      = 8
    MULTIPLICATION                 = 9
    DIVISION                       = 10
    MODULO                         = 11
    ADDITION                       = 12
    SUBTRACTION                    = 13
    BITWISE_LEFT_SHIFT             = 14
    BITWISE_RIGHT_SHIFT            = 15
    GREATER_THAN                   = 16
    LESS_THAN                      = 17
    GREATER_THAN_OR_EQUALS         = 18
    LESS_THAN_OR_EQUALS            = 19
    EQUALS                         = 20
    NOT_EQUALS                     = 21
    BITWISE_AND                    = 22
    BITWISE_XOR                    = 23
    BITWISE_OR                     = 24
    LOGICAL_AND                    = 25
    LOGICAL_OR                     = 26
    ASSIGNMENT                     = 27
    MULTIPLICATION_ASSIGNMENT      = 28
    DIVISION_ASSIGNMENT            = 29
    MODULO_ASSIGNMENT              = 30
    ADDITION_ASSIGNMENT            = 31
    SUBTRACTION_ASSIGNMENT         = 32
    BITWISE_LEFT_SHIFT_ASSIGNMENT  = 33
    BITWISE_RIGHT_SHIFT_ASSIGNMENT = 34
    BITWISE_AND_ASSIGNMENT         = 35
    BITWISE_XOR_ASSIGNMENT         = 36
    BITWISE_OR_ASSIGNMENT          = 37


@dataclass
class TheirsceBaseInstruction:
    mnemonic: str = field(default=False, init=False)
    type: InstructionType = field(default=False, init=False)
    #size: int


@dataclass
class TheirsceAluInstruction(TheirsceBaseInstruction):
    operation: AluOperation
    mnemonic = "ALU"
    type = InstructionType.ALU

    def __post_init__(self):
        self.mnemonic = self.operation.name


@dataclass
class TheirscePushInstruction(TheirsceBaseInstruction):
    value: int
    mnemonic = "PUSH"
    type = InstructionType.PUSH


@dataclass
class TheirsceSyscallInstruction(TheirsceBaseInstruction):
    function_index: int
    function_name: str
    mnemonic = "SYSCALL"
    type = InstructionType.SYSCALL


@dataclass
class TheirsceLocalCallInstruction(TheirsceBaseInstruction):
    destination: int
    reserve: int
    mnemonic = "CALL"
    type = InstructionType.LOCAL_CALL


@dataclass
class TheirsceAcquireInstruction(TheirsceBaseInstruction):
    params: list[int]
    variables: int
    mnemonic = "ACQUIRE"
    type = InstructionType.ACQUIRE


@dataclass
class TheirsceBreakInstruction(TheirsceBaseInstruction):
    param: int
    mnemonic = "BREAK"
    type = InstructionType.BREAK


@dataclass
class TheirsceBranchInstruction(TheirsceBaseInstruction):
    destination: int
    branch_type: BranchType
    mnemonic = ""
    type = InstructionType.BRANCH

    def __post_init__(self):
        self.mnemonic = self.branch_type.name


@dataclass
class TheirsceReturnInstruction(TheirsceBaseInstruction):
    is_void: bool
    mnemonic = "RETURN"
    type = InstructionType.RETURN

    def __post_init__(self):
        if self.is_void:
            self.mnemonic += "_VOID"


@dataclass
class TheirsceStringInstruction(TheirsceBaseInstruction):
    text: str
    offset: int
    mnemonic = "STRING"
    type = InstructionType.STRING


@dataclass
class TheirsceReferenceInstruction(TheirsceBaseInstruction):
    ref_type: VariableType
    scope: ReferenceScope
    offset: int
    shift:  int
    mnemonic = "REF"
    type = InstructionType.REFERENCE


@dataclass
class TheirsceSpecialReferenceInstruction(TheirsceBaseInstruction):
    mnemonic = "SP_REF"
    type = InstructionType.SP_REF