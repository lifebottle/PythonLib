import re
import string

NAMES = {
    "Veigue": 1,
    "Mao": 2,
    "Eugene": 3,
    "Annie": 4,
    "Tytree": 5,
    "Hilda": 6,
    "Claire": 7,
    "Agarte": 8,
    "Annie (NPC)": 9,
    "Leader": 0x1FFF,
}

COLORS = {
    "Blue": 1,
    "Red": 2,
    "Purple": 3,
    "Green": 4,
    "Cyan": 5,
    "Yellow": 6,
    "White": 7,
    "Grey": 8,
    "Black": 9,
}

ITALICS = {
    "/Italic": 0,
    "Italic": 10,
}

TAGS = {
    "nl": 0x1,
    "cr": 0x2,
    "var": 0x4,
    "color": 0x5,
    "scale": 0x6,
    "speed": 0x7,
    "italic": 0x8,
    "nmb": 0x9,
    "ptr": 0xA,
    "name": 0xB,
    "item": 0xC,
    "icon": 0xD,
    "font": 0xE,
    "voice": 0xF,
    "unk13": 0x13,
    "unk14": 0x14,
    "unk15": 0x15,
    "unk16": 0x16,
    "unk17": 0x17,
    "unk18": 0x18,
    "unk19": 0x19,
    "unk1A": 0x1A,
}

FRIENDLY_TAGS = dict()
FRIENDLY_TAGS.update(NAMES)
FRIENDLY_TAGS.update(COLORS)
FRIENDLY_TAGS.update(ITALICS)

INDENT_CHAR = "    "

COMMON_TAG = r"(<[\w/]+:?\w+>)"
HEX_TAG = r"(\{[0-9A-F]{2}\})"
PRINTABLE_CHARS = "".join(
    (string.digits, string.ascii_letters, string.punctuation, " ")
)


def indent_lines(lines: list[str], level: int) -> list[str]:
    new_lines = list()
    for line in lines:
        new_lines.append(f"{INDENT_CHAR * level}{line}")
    return new_lines


def indent_line(line: str, level: int) -> str:
    return f"{INDENT_CHAR * level}{line}"


def text_to_cstr(text: str, is_name: bool = False) -> str:
    output = ""
    multi_regex = HEX_TAG + "|" + COMMON_TAG + r"|(\n)" + r"|(ー)"
    tokens = [sh for sh in re.split(multi_regex, text) if sh]

    for token in tokens:
        # Hex literals
        if re.match(HEX_TAG, token):
            output += f" \\x{int(token[1:3], 16):02X}"

        # Tags
        elif re.match(COMMON_TAG, token):
            tag, param, *_ = token[1:-1].split(":") + [None]

            # (In)Sanity check
            if "unk" in tag.lower():
                raise ValueError(
                    f"Don't use sce tags, makes no sense!\nProblem text -> {text}"
                )

            if param is not None:
                param_bytes = int(param, 16).to_bytes(4, byteorder="little")
                raw = ",".join([f"{b:02X}" for b in param_bytes])
                output += f" {tag.upper()}({raw}) "
            else:
                if is_name and tag in NAMES:
                    ntag = tag.replace("(", "").replace(")", "")
                    output += f" NAME({ntag.upper()}) "
                elif tag in TAGS:
                    output += f'"\\x{TAGS[tag]:02X}"'
                elif tag in FRIENDLY_TAGS:
                    if tag == "/Italic":
                        output += " NO_ITALIC "
                    else:
                        output += f" {tag.upper()} "
        elif token == "\n":
            output += " NL\n"
        elif token == "ー":
            output += " EM_DASH "
        else:
            if is_name:
                if token == "&":
                    output += '" and "'
                else:
                    names = [f'NAME("{x}")' for x in token.split("&")]
                    output += '" and "'.join(names)
            else:
                output += f'"{token}"'

    return output.strip()
