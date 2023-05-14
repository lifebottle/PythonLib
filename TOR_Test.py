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
t = tool.pack_Skit_File("14635.3.pak2")









files = os.listdir("abcde_lauren")
for file in files:
    
    tool.extract_abcde_text("abcde_lauren/{}".format(file))
    
    
