from ToolsTales import ToolsTales
import subprocess
from dicttoxml import dicttoxml
import json
import struct
import shutil
import os
import re
import pandas as pd
import xml.etree.ElementTree as ET
import lxml.etree as etree
import comptolib
from xml.dom import minidom
from pathlib import Path
import string
import io

class ToolsTODDC(ToolsTales):
    
    
    def __init__(self, tbl):
        
        self.gameName = "TODDC"
        self.repo_name = "Tales-of-Destiny-DC"
        self.basePath = os.getcwd()
        
        
        with open("../Tales-of-Destiny-DC/Data/Misc/toddc.tbl", encoding="utf-8") as f:
            data = f.readlines()
            hex_list = [bytes.fromhex(str(ele.split("=",1)[0])) for ele in data]
            self.itable = dict([[ele.split("=",1)[1].replace("\n",""), bytes.fromhex(ele.split("=",1)[0])] for ele in data])
            
     
            
        #with open("../{}/Data/{}/Misc/{}".format(repo_name, gameName, tblFile)) as f:
        #    jsonRaw = json.load(f)
        #    self.jsonTblTags ={ k1:{ int(k2,16) if (k1 != "TBL") else k2:v2 for k2,v2 in jsonRaw[k1].items()} for k1,v1 in jsonRaw.items()}
          
        #self.itable = dict([[i, struct.pack(">H", int(j))] for j, i in self.jsonTblTags['TBL'].items()])
        #self.itags = dict([[i, j] for j, i in self.jsonTblTags['TAGS'].items()])
        #self.inames = dict([[i, j] for j, i in self.jsonTblTags['NAMES'].items()])
        #self.icolors = dict([[i, j] for j, i in self.jsonTblTags['COLORS'].items()])
        
        
        with open("../{}/Data/{}/Menu/MenuFiles.json".format(self.repo_name, self.gameName)) as f:
           self.menu_files_json = json.load(f)
           
        