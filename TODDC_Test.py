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


tool = ToolsTODDC.ToolsTODDC("toddc.tbl")

ele = tool.menu_files_json[0]
tool.extract_Menu_File(ele)

