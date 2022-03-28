import ToolsTODDC
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


tool = ToolsTODDC.ToolsTODDC("TBL_All.json")

ele = tool.menu_files_json[0]
tool.extract_Menu_File(ele)

repo_name = "Tales-Of-Destiny-DC"
tblFile = "TBL_ALL.json"
with open("../{}/Data/Misc/{}".format(repo_name, tblFile), encoding="utf-8") as f:
    jsonRaw = json.load(f)
    jsonTblTags ={ k1:{ int(k2) if (k2 != "TBL") else int(k2):v2 for k2,v2 in jsonRaw[k1].items()} for k1,v1 in jsonRaw.items()}
    #jsonTblTags = {k2:v2 for k2,v2 in jsonRaw[k1].items()} for k1,v1 in jsonRaw.items()}
    

TAGS = jsonTblTags['TAGS']

with open("../Data/Tales-Of-Destiny-DC/Menu/New/00016/00016_0000d.unknown", "rb") as fileRead:
    
    
    fileRead.seek(0x3C87D)
    b = fileRead.read(1)
        
    b = ord(b)
    finalText=""
    if (b >= 0x99 and b <= 0x9F) or (b >= 0xE0 and b <= 0xEB):
        c = (b << 8) + ord(fileRead.read(1))
       
        # if str(c) not in json_data.keys():
        #    json_data[str(c)] = char_index[decode(c)]
        try:
            finalText += (jsonTblTags['TBL'][str(c)])
        except KeyError:
            b_u = (c >> 8) & 0xff
            b_l = c & 0xff
            finalText += ("{%02X}" % b_u)
            finalText += ("{%02X}" % b_l)
    elif b == 0x1:
        finalText += ("\n")
    elif b in (0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0x9, 0xB, 0xC, 0xD, 0xE, 0xF):
        b2 = struct.unpack("<L", fileRead.read(4))[0]
        if b in TAGS:
            tag_name = TAGS.get(b)
            
            tag_param = None
            tag_search = tag_name.upper()
            if (tag_search in jsonTblTags.keys()):
                tags2 = jsonTblTags[tag_search]
                tag_param = tags2.get(b2, None) 
            if tag_param != None:
                finalText += tag_param
            else:
                finalText += ("<%s:%08X>" % (tag_name, b2))
        else:
            finalText += "<%02X:%08X>" % (b, b2)