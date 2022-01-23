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

class ToolsTOR(ToolsTales):
    
    POINTERS_BEGIN = 0xD76B0                                            # Offset to DAT.BIN pointer list start in SLPS_254.50 file
    POINTERS_END   = 0xE60C8                                            # Offset to DAT.BIN pointer list end in SLPS_254.50 file
    HIGH_BITS      = 0xFFFFFFC0
    LOW_BITS       = 0x3F
    PRINTABLE_CHARS = "".join(
            (string.digits, string.ascii_letters, string.punctuation, " ")
        )
    
    #Path to used
    datBinPath       = '../Data/Disc/Original/DAT.BIN'
    elfPathExtract   = '../Data/Disc/Original/SLPS_254.50'
    storyPathArchives= '../Data/Story/SCPK'                        #Story XML files will be extracted here                      
    storyPathXML     = '../Data/Story/XML/'                     #SCPK will be repacked here
    skitPathArchives = '../Data//Skits/'                        #Skits XML files will be extracted here              
    datPathExtract   = '../Data/DAT/'
    allPathInsert    = '../Data/Disc/PSP_GAME/USRDIR'    
    
    def __init__(self, tbl):
        
        super().__init__("TOR", tbl)
        
        with open("TBL_All.json") as f:
            jsonRaw = json.load(f)
            self.jsonTblTags ={ k1:{ int(k2,16) if (k1 != "TBL") else k2:v2 for k2,v2 in jsonRaw[k1].items()} for k1,v1 in jsonRaw.items()}
                
     
        
        
    def get_pointers(self):

        f = open(self.elfPathExtract , "rb")
    
        f.seek(self.POINTERS_BEGIN, 0)
        pointers = []
    
        while f.tell() < self.POINTERS_END:
            
            p = struct.unpack("<L", f.read(4))[0]
            pointers.append(p)
    
        f.close()
        return pointers

    
    # Extract the story files
    def extractAllStory(self):
        
        print("Extracting Story")
        self.mkdir( self.storyPathXML)
        listFiles = [self.datPathExtract + 'SCPK/' + ele for ele in os.listdir( os.path.join(self.datPathExtract, "SCPK"))]
        for scpkFile in listFiles:
            self.extractTheirSceXML(scpkFile)
        
    def get_theirsce_from_scpk(self, scpk)->bytes:
        header = scpk.read(4)
    
        if header != b"SCPK":
            # sys.exit(f"{file} is not a .scpk file!")
            raise ValueError("File is not a .scpk file!")
    
        scpk.read(4)
        nbFiles = struct.unpack("<L", scpk.read(4))[0]
        scpk.read(4)
        filesSize = []
        for i in range(nbFiles):
            filesSize.append(struct.unpack("<L", scpk.read(4))[0])
    
        for i in range(nbFiles):
            data = scpk.read(filesSize[i])
    
            if self.is_compressed(data):
                data = comptolib.decompress_data(data)
            
            if data[:8] == b"THEIRSCE":
                return io.BytesIO(data)
    
        return None
    
    def extraxtStoryPointers(self, theirsce, strings_offset, fsize):
        
        
        pointers_offset = []
        texts_offset = []
        
        
        while theirsce.tell() < strings_offset:
            b = theirsce.read(1)
            if b == b"\xF8":
                addr = struct.unpack("<H", theirsce.read(2))[0]
                if (addr < fsize - strings_offset) and (addr > 0):
                    # theirsce_data[name].append(theirsce.tell() - 2)
                    pointers_offset.append(theirsce.tell() - 2)
                    texts_offset.append(addr + strings_offset)
        return pointers_offset, texts_offset
        
    
    #Convert a bytes object to text using TAGS and TBL in the json file
    def bytesToText(self, theirsce):
    
        finalText = ''
        TAGS = self.jsonTblTags['TAGS']
        
            
        b = theirsce.read(1)
        while b != b"\x00":
            b = ord(b)
            if (b >= 0x99 and b <= 0x9F) or (b >= 0xE0 and b <= 0xEB):
                c = (b << 8) + ord(theirsce.read(1))
               
                # if str(c) not in json_data.keys():
                #    json_data[str(c)] = char_index[decode(c)]
                try:
                    finalText += (self.jsonTblTags['TBL'][str(c)])
                except KeyError:
                    b_u = (c >> 8) & 0xff
                    b_l = c & 0xff
                    finalText += ("{%02X}" % b_u)
                    finalText += ("{%02X}" % b_l)
            elif b == 0x1:
                finalText += ("\n")
            elif b in (0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0x9, 0xB, 0xC, 0xD, 0xE, 0xF):
                b2 = struct.unpack("<L", theirsce.read(4))[0]
                if b in TAGS:
                    tag_name = TAGS.get(b)
                    tag_param = None
                    if (tag_name.upper() + "S") in globals():
                        tag_param = eval("%sS.get(b2, None)" % tag_name.upper())
                    if tag_param != None:
                        finalText += "<%s>" % tag_param
                    else:
                        finalText += ("<%s:%08X>" % (tag_name, b2))
                else:
                    finalText += "<%02X:%08X>" % (b, b2)
            elif chr(b) in self.PRINTABLE_CHARS:
                finalText += chr(b)
            elif b >= 0xA1 and b < 0xE0:
                finalText += struct.pack("B", b).decode("cp932")
            elif b in (0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19):
                finalText += "{%02X}" % b
                next_b = b""
                while next_b != b"\x80":
                    next_b = theirsce.read(1)
                    finalText += "{%02X}" % ord(next_b)
            elif b == 0x81:
                next_b = theirsce.read(1)
                if next_b == b"\x40":
                    finalText += "　"
                else:
                    finalText += "{%02X}" % b
                    finalText += "{%02X}" % ord(next_b)
            else:
                finalText += "{%02X}" % b
            b = theirsce.read(1)
       
            
        return finalText
    
    # Extract THEIRSCE to XML
    def extractTheirSceXML(self, scpkFileName):
     
        #Create the XML file
        root = etree.Element('SceneText')
        etree.SubElement(root, "OriginalName").text = scpkFileName
        
        stringsNode = etree.SubElement(root, "Strings")
        etree.SubElement(stringsNode, "Type").text = "Static"
        
        #Open the SCPK file to grab the THEIRSCE file
        with open(scpkFileName, "rb") as scpk:
            theirsce = self.get_theirsce_from_scpk(scpk)
            
        #Validate the header
        header = theirsce.read(8)
        if header != b"THEIRSCE":
            raise ValueError("No THEIRSCE header")
        
        #Start of the pointer
        pointer_block = struct.unpack("<L", theirsce.read(4))[0]
        
        #Start of the text and baseOffset
        strings_offset = struct.unpack("<L", theirsce.read(4))[0]
        
        #File size
        fsize = theirsce.getbuffer().nbytes
        theirsce.seek(pointer_block, 0)             #Go the the start of the pointer section
        pointers_offset, texts_offset = self.extraxtStoryPointers(theirsce, strings_offset, fsize)
        
        
        #Extract the text from each pointers
        textList = []
        for i in range(len(texts_offset)):
        
            #Extract the text
            theirsce.seek(texts_offset[i], 0)
            text = self.bytesToText(theirsce)
            
            #Add it to the XML node
            entry_node = etree.SubElement(stringsNode, "Entry")
            etree.SubElement(entry_node,"PointerOffset").text = str(pointers_offset[i])
            etree.SubElement(entry_node,"JapaneseText").text  = text
            etree.SubElement(entry_node,"EnglishText").text   = ''
            etree.SubElement(entry_node,"Notes").text         = ''
            
            if text == '':
                statusText = 'Done'
            else:
                statusText = 'To Do'
            etree.SubElement(entry_node,"Status").text        = statusText
    
    
        #Write the XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
    
        with open(os.path.join( self.storyPathXML, self.get_file_name(scpkFileName)+".xml"), "wb") as xmlFile:
            xmlFile.write(txt)
        
    # Extract the file DAT.BIn to the different directorties
    def extractMainArchive(self):
        
     
        f = open( self.datBinPath, "rb")
    
        pointers = self.get_pointers()
        total_files = len(pointers)
    
        for i in range(total_files - 1):
            remainder = pointers[i] & self.LOW_BITS
            start = pointers[i] & self.HIGH_BITS
            end = (pointers[i + 1] & self.HIGH_BITS) - remainder
            f.seek(start, 0)
            size = end - start
            if size == 0:
                # Ignore 0 byte files
                continue
            data = f.read(size)
            file_name = "%05d" % i
    
            if self.is_compressed(data):
                c_type = struct.unpack("<b", data[:1])[0]
                data = comptolib.decompress_data(data)
                extension = self.get_extension(data)
                final_path = self.datPathExtract + "/%s/%s.%d.%s" % (
                    extension.upper(),
                    file_name,
                    c_type,
                    extension,
                )
            else:
                extension = self.get_extension(data)
                final_path = self.datPathExtract + "/%s/%s.%s" % (
                    extension.upper(),
                    file_name,
                    extension,
                )
            
            folderPath = os.path.join( self.datPathExtract, extension.upper())
            self.mkdir( folderPath )
    
            with open(final_path, "wb") as output:
                output.write(data)
            print("Writing file %05d/%05d..." % (i, total_files), end="\r")
    
        print("Writing file %05d/%05d..." % (i, total_files))
        f.close()