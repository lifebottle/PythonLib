import ToolsTOR
import json
import struct
import comptolib
import io
import re
import string
import pandas as pd
import json


tool = ToolsTOR.ToolsTOR("tbl")

tool.bytes_to_text_with_offset("../Data/TOR/Disc/Original/SLPS_254.50", 0x119890)

with open("MenuFiles.json") as f:
    menu_files_json = json.load(f)
        
file_def = [ele for ele in menu_files_json if ele['File_Extract'] == "../Data/TOR/Menu/New/00013/00013_0000d.unknown" ][0]
tool.extract_Menu_File(file_def)
#tool.insert_Menu_File("../Data/TOR/Disc/Original/SLPS_254.50")



with open("00013.pak3", "rb") as f:
    
    data = f.read()
    

t = tool.get_pak_type(data)