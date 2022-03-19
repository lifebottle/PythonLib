import ToolsNDX
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
import cabarchive


tool = ToolsNDX.ToolsNDX("TBL_All.json")
tool.extract_Story_File("ep_010_030_0000.unknown")



tool.extract_FPS4()




tool.extract_All_Pak3()
tool.extract_All_Cab()
tool.extract_Main_Archive()

tool.bytes_to_text_with_offset("menu.unknown", 0x30FF2, b'')

base_path = "../Data/NDX/Menu/New/BT_DATA"
list_files = os.listdir(base_path)
for file in list_files:
    tool.extract_Cab(os.path.join( base_path, file), file.split(".")[0]+".bin")