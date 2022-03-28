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
        
        super().__init__("TODDC", tbl, "Tales-of-Destiny-DC")
           
        
