import csv
from collections import defaultdict
from typing import TextIO
import urllib.error
import urllib.request
from io import StringIO
from dataclasses import dataclass
from ..srt import TimeStamp, str_to_timestamp
from .text_util import text_to_cstr, indent_lines

URL = "https://docs.google.com/spreadsheets/d/1-XwzS7F0SaLlXwv1KS6RcTEYYORH2DDb1bMRy5VM5oo/gviz/tq?tqx=out:csv&sheet=Subs&range=A:M"

SUBTITLE_TYPES = [
    "TYPE_NORMAL",
    "TYPE_BOTTOM",
    "TYPE_POST_BATTLE",
]


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
