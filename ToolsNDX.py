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

class ToolsNDX(ToolsTales):
    
    
    POINTERS_BEGIN = 0xD76B0                                            # Offset to DAT.BIN pointer list start in SLPS_254.50 file
    POINTERS_END   = 0xE60C8                                            # Offset to DAT.BIN pointer list end in SLPS_254.50 file
    HIGH_BITS      = 0xFFFFFFC0
    LOW_BITS       = 0x3F
    
    
    
    #Path to used
    allDatOriginal   = '../Data/NDX/Disc/Original/PSP_GAME/USRDIR/all.dat'
    allDatNew        = '../Data/NDX/Disc/New/all.dat'
    elfOriginal      = '../Data/NDX/MISC/ULJS00293.BIN'
    elfNew           = '../Data/TOR/Disc/New/ULJS00293.BIN'
    storyPathArchives= '../Data/TOR/Story/SCPK/'                        #Story XML files will be extracted here                      
    storyPathXML     = '../Data/TOR/Story/XML/'                     #SCPK will be repacked here
    skitPathArchives = '../Data/TOR/Skits/'                        #Skits XML files will be extracted here              
    datPathExtract   = '../Data/TOR/DAT/' 
    
    def __init__(self, tbl):
        
        super().__init__("TOR", tbl)
        
        self.struct_byte_code = b'\x18\x00\x0C\x04'
        self.struct_strings_code = b'\x00\x00\x82\x02'
        
        
    def extract_Story_Pointers(self, f):
    
        f.read(12)
        baseOffset = struct.unpack('<I', f.read(4))[0]
        
        f.read(4)
        pointer_block_size = struct.unpack('<I', f.read(4))[0]
        blockSize = struct.unpack('<I', f.read(4))[0]
        read = 0
    
        structDict = dict()
        stringDict = dict()
        while read < pointer_block_size:
            b = f.read(4)
            if b == self.struct_byte_code:
                
                pointerOffset = f.tell()
                valueOffset = struct.unpack('<I', f.read(4))[0]
                structDict[pointerOffset] = valueOffset
                read += 4
            elif b == self.strings_byte_code:
                pointerOffset = f.tell()
                valueOffset  = struct.unpack('<I', f.read(4))[0]
                stringDict[pointerOffset] = valueOffset
                read += 4
            read += 4
            
        return structDict, stringDict, baseOffset, blockSize

    def buildStructEntry(self, storyFile, f, structDict, baseOffset, blockSize, root):
    
        #Extract pointers inside each structure
        pathFile = os.path.join(os.path.abspath(os.path.dirname(os.getcwd())))
        absoluteFileName = os.path.basename(storyFile)
    
        
        
        personPointers = []
        for (structOffset, structValueOffset) in structDict.items():
            
            
            #print("Struct : {}".format(hex(structValueOffset+baseOffset)))
            
            f.seek(structValueOffset + baseOffset, 0)
            
            #Unknown first pointer
            f.read(4)
            
            pointer          = struct.unpack('<I', f.read(4))[0]
            personAdd        = struct.unpack('<I', f.read(4))[0] + baseOffset
            personPointers.append(personAdd)
            
            textAdd          = struct.unpack('<I', f.read(4))[0] + baseOffset
            unknown1Add      = struct.unpack('<I', f.read(4))[0] + baseOffset
            unknown2Add      = struct.unpack('<I', f.read(4))[0] + baseOffset
            
            personText       = extractText(f, personAdd, textAdd - personAdd - 1, tbl)
            #print(personText)
            unknown1Text     = extractText(f, unknown1Add, unknown2Add - unknown1Add - 1, tbl)
            unknown2Text     = extractText(f, unknown2Add, structValueOffset + baseOffset - unknown2Add - 1, tbl)
            
            #Add all the nodes to the base Struct Node        
            structNode = etree.SubElement(root, "Struct")
            etree.SubElement(structNode, "PointerOffset").text = str(structOffset)
            etree.SubElement(structNode, "PointerUnknownValue").text = str(pointer)
            etree.SubElement(structNode, "Unknown1Text").text = unknown1Text
            etree.SubElement(structNode, "Unknown2Text").text = unknown2Text
            etree.SubElement(structNode, "TextOffset").text = str(personAdd)
            etree.SubElement(structNode, "PersonJapaneseText").text = personText
            etree.SubElement(structNode, "PersonEnglishText").text = "";
            
            
            #Extract each bubble of text and add it to the EntryList Node
            #entryListNode = etree.SubElement(structNode, "EntryList")
            
            
            japText         = extractText(f, textAdd, unknown1Add - textAdd - 1, tbl)
            listVoiceId     = re.findall("\((\w+)\)", japText)
            
            if len(listVoiceId) > 0:
                etree.SubElement(structNode, "Type").text = "VoiceId"
            else:
                etree.SubElement(structNode, "Type").text = "NoVoiceId"
                
            
            addEntry(japText, structNode, listVoiceId)
            
    
        return root, personPointers
            

    def buildStaticEntry(self, storyFile, f, stringDict, baseOffset, blockSize, root, personPointers):
        
        fileSize = os.path.getsize(storyFile) 
        stringOffset = [value+baseOffset for (key,value) in stringDict.items()]
        
        
        def getSize(ind, ele):
            
            listRes =[x for x in personPointers if x > ele]
            firstGreater = 1000000000000000
            if( len(listRes) > 0):
             
                firstGreater = listRes[0]
            return min(firstGreater, stringOffset[ind+1] ) - ele
            
        
        n = len(stringOffset)
        stringSize   = [ getSize(ind, ele) if ind < n-1 else fileSize - ele for (ind, ele) in enumerate(stringOffset)]
        
        i=0
        for (stringOffset, stringValueOffset) in stringDict.items():
            
            #print("Static : {}".format(hex( stringValueOffset+baseOffset)))
            staticNode = etree.SubElement(root, "Static")
            text = extractText(f, stringValueOffset + baseOffset, stringSize[i], tbl)
            #print(text)
            etree.SubElement(staticNode, "PointerOffset").text = str(stringOffset)
            etree.SubElement(staticNode, "TextOffset").text = str(stringValueOffset + baseOffset)
            etree.SubElement(staticNode, "JapaneseText").text = text
            etree.SubElement(staticNode, "EnglishText").text  = ""
            etree.SubElement(staticNode, "Notes").text = ""
            i=i+1
        return root
       
    def extract_Story_File(self, file):

        root = etree.Element('SceneText')
        etree.SubElement(root, "OriginalName").text = file
        
        fileName = os.path.splitext(file)[0]
        #print(file)
        
        
        #file = r"G:\TalesHacking\TOP_Narikiri\PSP_GAME\USRDIR\all\map\pack\ep_000_010\ep_000_010_0000.unknown"
        #file = r"G:\TalesHacking\TOP_Narikiri\Scripts\AMUI00.SCP.decompressed"
        with open(file, 'rb') as f:
            
            print("\nFILE :   {}\n".format(file))
          
            structDict, stringDict, baseOffset, blockSize = self.extract_Story_Pointers(f)
            
            fileFolder = os.path.basename(file).replace("_0000.unknown", "")
            root, personPointers = self.build_Struct_Entry(file, f,structDict, baseOffset, blockSize, root)
            
            #Write the static data to the XML  
            root = self.build_Static_Entry(file, f,stringDict, baseOffset, blockSize, tbl, root, personPointers)
    
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
        
        with open(os.path.join( r"G:\TalesHacking\TOP_Narikiri\GithubProject\TranslationApp\TranslationApp\bin\Debug", fileName+".xml"), "wb") as xmlFile:
            xmlFile.write(txt)
        
        