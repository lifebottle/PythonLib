import csv
from collections import defaultdict
from typing import TextIO
import urllib.error
import urllib.request
from io import StringIO
import re
from dataclasses import dataclass
import string


URL = "https://docs.google.com/spreadsheets/d/1-XwzS7F0SaLlXwv1KS6RcTEYYORH2DDb1bMRy5VM5oo/gviz/tq?tqx=out:csv&sheet=Subs&range=A:M"


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

SUBTITLE_TYPES = [
    "TYPE_NORMAL",
    "TYPE_BOTTOM",
    "TYPE_POST_BATTLE",
]


@dataclass
class TimeStamp:
    hours: int
    minutes: int
    seconds: int
    milis: int


@dataclass
class SubEntry:
    bd_file: int
    voice_id: int
    type: int
    priority: int
    start_time: TimeStamp
    end_time: TimeStamp
    character: str
    text: str


# TODO: Perhaps move this
rTIME_STAMP = r"(\d+):(\d+):(\d+)[.,](\d+)"
rTIME_STAMP_NO_HOUR = r"(\d+):(\d+)[.,](\d+)"


def str_to_timestamp(time_stamp: str) -> TimeStamp:
    colon_cnt = time_stamp.count(":")
    if colon_cnt == 2:
        times = [int(s) for s in re.findall(rTIME_STAMP, time_stamp)[0]]
        hours = times[0]
        minutes = times[1]
        seconds = times[2]
        milis = times[3]
    if colon_cnt == 1:
        times = [int(s) for s in re.findall(rTIME_STAMP_NO_HOUR, time_stamp)[0]]
        hours = 0
        minutes = times[0]
        seconds = times[1]
        milis = times[2]
    if colon_cnt == 0 or time_stamp.isspace():
        hours = 0
        minutes = 0
        seconds = 0
        milis = 0

    return TimeStamp(hours, minutes, seconds, milis)


def indent_lines(lines: list[str], level: int) -> list[str]:
    new_lines = list()
    for line in lines:
        new_lines.append(f"{INDENT_CHAR * level}{line}")
    return new_lines


def indent_line(line: str, level: int) -> str:
    return f"{INDENT_CHAR * level}{line}"


def text_to_cstr(text: str, is_name: bool = False) -> str:
    output = ""
    multi_regex = HEX_TAG + "|" + COMMON_TAG + r"|(\n)"
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
            output += " NL "
        else:
            if is_name and token != "&":
                output += f'NAME("{token}")'
            else: 
                output += f'"{token}"'

    return output.strip()


def row_to_subentry(row: dict) -> SubEntry:
    type = int(row["type"])
    priority = int(row["priority"])
    bd_file = int(row["bd_file"])
    voice_id = int(row["voice_id_dec"])

    # cleanup texts
    character: str = row["character"]
    character = character.strip()
    character = character.replace('"', '\\"')

    text: str = row["english_text"]
    text = text.strip()
    text = text.replace('"', '\\"')

    ts_start = str_to_timestamp(row["start_frame"])

    end_text: str = row["end_frame"]
    if end_text == "" or end_text.isspace() or end_text == "99:99.99":
        ts_end = TimeStamp(-1, -1, -1, -1)
    else:
        ts_end = str_to_timestamp(row["end_frame"])

    entry: SubEntry = SubEntry(
        bd_file, voice_id, type, priority, ts_start, ts_end, character, text
    )
    return entry


def entry_to_line_str(entry: SubEntry, index: int) -> list[str]:
    content = list()

    bd = entry.bd_file
    type = SUBTITLE_TYPES[entry.type]
    priority = entry.priority

    ts_start = entry.start_time
    start_text = (
        f"TS_TO_FRAMES({ts_start.minutes}, {ts_start.seconds}, {ts_start.milis})"
    )

    ts_end = entry.end_time
    if ts_end.seconds == -1:
        end_text = "FRAME_MAX"
    else:
        end_text = f"TS_TO_FRAMES({ts_end.minutes}, {ts_end.seconds}, {ts_end.milis})"

    name = text_to_cstr(entry.character, True)
    text = text_to_cstr(entry.text)

    # Add the Voice_Line structure
    content.append(f"const Voice_Line line_{bd:05d}_{index} = {{")
    content.append(f"    {type},")
    content.append(f"    {priority},")
    content.append(f"    {start_text},")
    content.append(f"    {end_text},")
    content.append(f'    {name} ": " {text}')
    content.append("};")
    return content


def entry_list_to_str(entries: list[SubEntry]) -> list[str]:
    content = list()

    total = len(entries)
    file = entries[0].bd_file
    content.append(f"const Voice_Line* lines_{file:05d}[{total}] = {{")

    temp = [f"&line_{file:05d}_{i}," for i, _ in enumerate(entries)]
    temp[-1] = temp[-1][:-1]
    content.extend(indent_lines(temp, 1))

    content.append("};")

    return content


def grab_online_csv_data() -> tuple[bool, StringIO]:
    try:
        response = urllib.request.urlopen(URL)
        data = response.read().decode("utf8")

        sdata = StringIO(data)
        return False, sdata
    except urllib.error.URLError:
        return True, StringIO()


def generate_header_lines(sdata: TextIO) -> list[str]:
    reader = csv.DictReader(sdata, dialect=csv.unix_dialect, quotechar='"')
    rows = [row for row in reader if row["Insert"].strip().upper() == "TRUE"]

    # Group rows by category_id and bd_file then make damn sure
    # everything is sorted
    grouped_rows: dict[int, dict[int, list[SubEntry]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for row in rows:
        category = int(row["category_id_dec"])
        bd_file = int(row["bd_file"])

        entry = row_to_subentry(row)
        grouped_rows[category][bd_file].append(entry)

    # sort inner dict
    total_count = 0
    for k, v in grouped_rows.items():
        grouped_rows[k] = dict(sorted(v.items()))
        total_count += len(v)

    # sort outer dict
    grouped_rows = dict(sorted(grouped_rows.items()))

    # Start creating the header file content
    hdr = [
        "/* This file is autogenerated */",
        "#pragma once",
        "",
        '#include "types.h"',
        '#include "Sub_Types.h"',
        '#include "Util.h"',
        "",
        f"const int Battle_Table_Count = {total_count};",  # Total number of entries
        "",
    ]

    hdr.append("#pragma region Lines")
    for category, bd_files in grouped_rows.items():
        hdr.append(f"    #pragma region Lines for Category 0x{category:02X}")
        for bd_file, entries in bd_files.items():
            for i, entry in enumerate(entries):
                lines = entry_to_line_str(entry, i)
                hdr.extend(indent_lines(lines, 2))
        hdr.append(f"    #pragma endregion Lines for Category 0x{category:02X}")
        hdr.append("")
    hdr.pop()
    hdr.append("#pragma endregion Lines")
    hdr.append("")
    hdr.append("")

    # Generate Voice_Line* pointers for each bd_file
    hdr.append("#pragma region Line pointers")
    for category, bd_files in grouped_rows.items():
        for bd_file, entries in bd_files.items():
            lines = entry_list_to_str(entries)
            hdr.extend(indent_lines(lines, 1))
            hdr.append("")
    hdr.pop()
    hdr.append("#pragma endregion Line pointers")
    hdr.append("")
    hdr.append("")

    # Generate Battle_Subs_Table for each category
    hdr.append("const Battle_Subs_Table battle_subs_tables[Battle_Table_Count] = {")
    for category, bd_files in grouped_rows.items():
        hdr.append(f"    // Category 0x{category:02X}")
        for bd_file, entries in bd_files.items():
            voice = entries[0].voice_id
            # Add each entry in the category-specific table
            hdr.append("    {")
            hdr.append(f"        CAT_PAIR_TO_ID({category}, {voice}),")
            hdr.append(f"        ARRAY_COUNT(lines_{bd_file:05d}),")
            hdr.append(f"        lines_{bd_file:05d}")
            hdr.append("    },")
        # Close the table for this category
        # header_content.append(f"// Category 0x{category:02X}")
        hdr.append("")
    hdr.pop()
    hdr[-1] = hdr[-1].rstrip(",")  # Remove trailing comma
    hdr.append("};")
    hdr.append("")

    return hdr
