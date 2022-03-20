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


tool = ToolsTOR.ToolsTOR("TBL_All.json")
tool.pakComposer_Comptoe("11181.pak3", "-d", "-3", True, r"G:\TalesHacking\PythonLib_Playground\Data\TOR\Menu\New")

tool.extract_All_Menu()



tool.extract_All_Story_Files(debug=True)

t = tool.pack_Story_File("10247.scpk")

tool.pack_Main_Archive()





files = os.listdir("abcde_lauren")
for file in files:
    
    tool.extract_abcde_text("abcde_lauren/{}".format(file))
    
    
