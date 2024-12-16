from itertools import groupby
from pathlib import Path
import re
from dataclasses import dataclass

@dataclass
class TimeStamp:
    hours: int
    minutes: int
    seconds: int
    milis: int

@dataclass
class SrtSub:
    number: int
    start: TimeStamp
    end: TimeStamp
    content: str

rTIME_STAMP = r"(\d+):(\d+):(\d+)[.,](\d+)"
rTIME_STAMP_NO_HOUR = r"(\d+):(\d+)[.,](\d+)"

def str_to_timestamp(time_stamp: str) -> TimeStamp:
    colon_cnt = time_stamp.count(":")
    if colon_cnt == 2:
        # For HH:MM:SS.mmm
        times = re.findall(rTIME_STAMP, time_stamp)
        if times:
            hours, minutes, seconds, milis_str = times[0]
            hours, minutes, seconds = map(int, (hours, minutes, seconds))
            milis = int((milis_str + "000")[:3])  # Normalize to 3 digits
        else:
            raise ValueError("Invalid time_stamp format for HH:MM:SS.mmm")

    elif colon_cnt == 1:
        # For MM:SS.mmm
        times = re.findall(rTIME_STAMP_NO_HOUR, time_stamp)
        if times:
            minutes, seconds, milis_str = times[0]
            minutes, seconds = map(int, (minutes, seconds))
            milis = int((milis_str + "000")[:3])  # Normalize to 3 digits
            hours = 0
        else:
            raise ValueError("Invalid time_stamp format for MM:SS.mmm")
    if colon_cnt == 0 or time_stamp.isspace():
        hours = 0
        minutes = 0
        seconds = 0
        milis = 0

    return TimeStamp(hours, minutes, seconds, milis)

def get_subs(filename: Path) -> list[SrtSub]:
    # simple srt parser from: https://stackoverflow.com/a/23620587
    # "chunk" our input file, delimited by blank lines
    with open(filename, encoding="utf-8-sig") as f:
        res = [list(g) for b, g in groupby(f, lambda x: bool(x.strip())) if b]

    subs = list()

    for sub in res:
        assert len(sub) >= 3, "Invalid subtitle entry in file: %s" % filename
        sub = [x.strip() for x in sub]
        number = sub[0]
        start, end = [str_to_timestamp(t) for t in sub[1].split(" --> ")]
        content = "\n".join(sub[2:])
        subs.append(SrtSub(int(number), start, end, content))

    return subs
