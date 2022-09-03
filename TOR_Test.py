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
tool.pack_Menu_File("../Data/Tales-Of-Rebirth/Disc/Original/SLPS_254.50")
tool.pack_Main_Archive()


tool.extract_All_Story_Files(debug=True)

t = tool.pack_Story_File("10247.scpk")







files = os.listdir("abcde_lauren")
for file in files:
    
    tool.extract_abcde_text("abcde_lauren/{}".format(file))
    
    
