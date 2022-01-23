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
from xml.dom import minidom
import re
import collections
import comptolib
import lxml.etree as ET

class ToolsTales:
    
    
    def __init__(self, gameName, tblFile):
        
        self.gameName = gameName
        self.basePath = os.getcwd()
        self.miscPath = os.path.join( self.basePath, "../Data/Misc/")
        
        #Load tbl file
        tblList = []
        with open(r"ToR.tbl", "r", encoding="utf-8") as tblFile:
            lines = tblFile.readlines()
            tblList = [ [ bytes.fromhex(ele.split("=",1)[0]), ele.split("=",1)[1].replace("\n","")]  for ele in lines]

        tempDict = dict( tblList)        
        
        tblDict = dict()
        for k in sorted( tempDict, key=len, reverse=True):
            tblDict[k] = tempDict[k]
        
        
    def mkdir(self, d):
        try: os.mkdir(d)
        except: pass
            
    ##############################
    #
    # Utility functions
    #
    ##############################
    
    # Compress and Decompress pak files
    # action is -d or -c
    # fileType : -0, -1 or -3
    # basePath is the location of the PAK file you want to compress/decompress
    def pakComposerAndComptoe(self, fileName, action, fileType):
          
        #Delete the file if already there    
        if (action == '-c'):
            if os.path.exists(fileName):
                os.remove( fileName.replace(".pak{}", fileType[1]))
                
        #Run Pakcomposer with parameters
        args = [ "pakcomposer", action, fileName, fileType, "-v", "-u", "-x"]
        listFile = subprocess.run(
            args
            )
        
    def get_extension(self, data):
        if data[:4] == b"SCPK":
            return "scpk"
    
        if data[:4] == b"TIM2":
            return "tm2"
    
        if data[:4] == b"\x7FELF":
            return "irx"
    
        if data[:8] == b"IECSsreV":
            if data[0x50:0x58] == b"IECSigaV":
                return "hd"
            elif data[0x30:0x38] == b"IECSidiM":
                return "sq"
    
        if data[:16] == b"\x00" * 0x10:
            if data[16:18] != b"\x00\x00":
                return "bd"
    
        if data[:8] == b"THEIRSCE":
            return "theirsce"
    
        if data[:3] == b"MFH":
            return "mfh"
    
        if data[:4] == b"EBG\x00":
            return "ebg"
    
        if data[:4] == b"anp3":
            return "anp3"
    
        if data[:4] == b"EFFE":
            return "effe"
    
        # 0x####BD27 is the masked addiu sp,sp,#### mips instruction
        # These are overlay files, containing compiled MIPS assembly
        if data[2:4] == b"\xBD\x27":
            return "ovl"
    
        if data[6:8] == b"\xBD\x27":
            return "ovl"
    
        is_pak = self.get_pak_type(data)
        if is_pak != None:
            return is_pak
        
        if len(data) > 0x400:
            size = struct.unpack("<I", data[0x400:0x404])[0]
            if len(data) == size + 0x400:
                return "tmsk"
    
        # Didn't match anything
        return "bin"
        def is_compressed(self, data):
            if len(data) < 0x09:
                return False
        
            expected_size = struct.unpack("<L", data[1:5])[0]
            tail_data = abs(len(data) - (expected_size + 9))
            if expected_size == len(data) - 9:
                return True
            elif tail_data <= 0x10 and data[expected_size + 9 :] == b"#" * tail_data:
                return True # SCPK files have these trailing "#" bytes :(
            return False
    
    def get_pak_type(self,data):
        is_aligned = False
    
        if len(data) < 0x8:
            return None
    
        files = struct.unpack("<I", data[:4])[0]
        first_entry = struct.unpack("<I", data[4:8])[0]
    
        # Expectations
        pak1_header_size = 4 + (files * 8)
        pakN_header_size = 4 + (files * 4)
    
        # Check for alignment
        if first_entry % 0x10 == 0:
            is_aligned = True
            aligned_pak1_size = pak1_header_size + (0x10 - (pak1_header_size % 0x10))
            aligned_pakN_size = pakN_header_size + (0x10 - (pakN_header_size % 0x10))
    
        # First test pak0 (hope there are no aligned pak0 files...)
        if len(data) > pakN_header_size:
            calculated_size = 0
            for i in range(4, (files + 1) * 4, 4):
                calculated_size += struct.unpack("<I", data[i : i + 4])[0]
            if calculated_size == len(data) - pakN_header_size:
                return "pak0"
    
        # Test for pak1 & pak3
        if is_aligned:
            if aligned_pak1_size == first_entry:
                return "pak1"
            elif aligned_pakN_size == first_entry:
                return "pak3"
        else:
            if pak1_header_size == first_entry:
                return "pak1"
            elif pakN_header_size == first_entry:
                return "pak3"
    
        # Test for pak2
        offset = struct.unpack("<I", data[0:4])[0]
    
        if data[offset:offset+8] == b"THEIRSCE":
            return "pak2"
        elif data[offset:offset+8] == b"IECSsreV":
            return "apak"
    
        # Didn't match anything
        return None
    
    def is_compressed(self,data):
        if len(data) < 0x09:
            return False
    
        expected_size = struct.unpack("<L", data[1:5])[0]
        tail_data = abs(len(data) - (expected_size + 9))
        if expected_size == len(data) - 9:
            return True
        elif tail_data <= 0x10 and data[expected_size + 9 :] == b"#" * tail_data:
            return True # SCPK files have these trailing "#" bytes :(
        return False


    def makeCab(self):
        print("CAB")
    
    
    def get_file_name(self, path):
        return os.path.splitext(os.path.basename(path))[0]

    def findall(self, p, s):
        '''Yields all the positions of
        the pattern p in the string s.'''
        i = s.find(p)
        while i != -1:
            yield i
            i = s.find(p, i+1)
    
    def bytesToText(self, text):
        print("Converting")
        
        
        def findall(p, s):
            '''Yields all the positions of
            the pattern p in the string s.'''
            i = s.find(p)
            while i != -1:
                yield i
                i = s.find(p, i+1)
            
            
        
        text = '[Veigue] is a nice guy'
        textInitial = text
        dictFound = dict()
        listFoundPositions = []
        listKeys = []
        listValues = []
        
        #Loop over all elements of the tbl file
        #key is in bytes
        #value is the text
        tblDict = dict()
        for key,value in tblDict.items():
            
            #Look for all the matches 
            matches = [i for i in findall(value, textInitial) if i not in listFoundPositions]
            
            lenMatches = len(matches)
            if lenMatches > 0:
                print(value)
                text = text.replace(value, '')  
                
                lenValue = len(value)
                x = [listFoundPositions.extend( list(range(posStart, posStart+lenValue))) for posStart in matches]
                listKeys.extend( matches)
                listValues.extend( [key] * lenMatches)
            if text == "":
                break
        
            b''.join([listValues[pos] for pos in sorted( listKeys)])
                
  
    
            
        
        
        
      
    #############################
    #
    # Insertion of texts and packing of files
    #
    #############################
    
    def insertAllMenu(self):
        print("Inserting Menus")
    
    
    def insertStoryFile(fileName):
        print("Inserting story file: {}".format(fileName))
        
    def insertAllStory(self):
        print("Inserting Story")
        
    def insertAllSkits(self):
        print("Inserting Skits")
        
    
    def insertAll(self):
        
        self.insertAllMenu()
        
        self.insertAllStory()
        
        self.insertAllSkits()

        
    #############################
    #
    # Extraction of files and unpacking
    #
    #############################
    
    def extractDecryptedEboot(self):
        print("Extracting Eboot")
        args = ["deceboot", os.path.join(self.basePath,"../Data/Disc/Original/PSP_GAME/SYSDIR/EBOOT.BIN"), os.path.join("../Data/Misc/EBOOT_DEC.BIN")]
        listFile = subprocess.run(
            args,
            cwd= self.basePath,
            )
               
        
    def extractAllMenu(self):
        print("Extracting menu")
    
    def extractAllStory(self):
        print("Extracting Story")
        
    def extractAllSkits(self):
        print("Extracting Skits")
        
    def extractMainArchive(self):
        print("Main Archive")
        
        
    def unpackGame(self):
        
        self.extractMainArchive()
        
        self.extractAllStory()
    
        self.extractAllSkits()
    
    #Create the final Iso or Folder that will help us run the game translated
    def packGame(self):
        
        #Insert the text translated and repack the files at the correct place
        self.insertAll()
        
        #
        
                     