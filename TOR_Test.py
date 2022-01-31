import ToolsTOR
import json
import struct
import comptolib
import io
import re
import string
import pandas as pd


tool = ToolsTOR.ToolsTOR("tbl")
tool.extractMainArchive()


tool.extractAllStory()

tool.insertStoryFile("10247.scpk")
tool.insertMainArchive()


text = '自由青年'
text = '<Blue><Eugene> is awesome'
bytesFinal = tool.textToBytes(text)

def is_compressed(data):
    if len(data) < 0x09:
        return False

    expected_size = struct.unpack("<L", data[1:5])[0]
    tail_data = abs(len(data) - (expected_size + 9))
    if expected_size == len(data) - 9:
        return True
    elif tail_data <= 0x10 and data[expected_size + 9 :] == b"#" * tail_data:
        return True # SCPK files have these trailing "#" bytes :(
    return False
        


with open("event.dat", "rb") as f:
    data = f.read()
  

is_compressed(data)

comptolib.decompress_data(data)