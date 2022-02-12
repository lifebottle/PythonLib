import ToolsTOR
import json
import struct
import comptolib
import io
import re
import string
import pandas as pd
import json
import os
import lxml.etree as etree


tool = ToolsTOR.ToolsTOR("tbl")
with open("MenuFiles.json") as f:
    menu_files_json = json.load(f)
        
file_def = [ele for ele in menu_files_json if ele['File_Extract'] == "../Data/TOR/Disc/Original/SLPS_254.50" ][0]
tool.extract_Menu_File(file_def)





myDir = "../Data/TOR/DAT"
extensions = ['bin', 'pak1', 'pak2', 'pak3', 'unknown', 'ovl', 'scpk']
for path, subdirs, files in os.walk(myDir):
    for name in [ele for ele in files if ele.split(".")[-1] in extensions]:

        print("File : {}".format(name))
        tool.bytes_to_text_with_offset(os.path.join(path,name), 0x0)






tool.bytes_to_text_with_offset("../Data/TOR/Disc/Original/SLPS_254.50", 0x0)



list_files = os.listdir("abcde_lauren")
for file in list_files:
    tool.extract_abcde_text("abcde_lauren/" + file)



tool.insert_Menu_File("../Data/TOR/Disc/Original/SLPS_254.50")



