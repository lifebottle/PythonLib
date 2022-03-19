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
import fps4

class ToolsNDX(ToolsTales):
    
    
    POINTERS_BEGIN = 0x1FF624                                            # Offset to all.dat
    POINTERS_END   = 0xE60C8                                            

    
    
    #Path to used
    allDat_Original   = '../Data/NDX/Disc/Original/PSP_GAME/USRDIR/all.dat'
    allDat_New        = '../Data/NDX/Disc/New/all.dat'
    elf_Original      = '../Data/NDX/MISC/ULJS00293.BIN'
    elf_New           = '../Data/NDX/Disc/New/ULJS00293.BIN'
    story_Path        = '../Data/NDX/Story/'                                                         
    skits_Path         = '../Data/NDX/Skits/'
    events_Path         = '../Data/NDX/Events/'                                    
    all_Path_Extract   = '../Data/NDX/DAT/' 
    
    def __init__(self, tbl):
        
        super().__init__("NDX", tbl)
        
        self.struct_byte_code = b'\x18\x00\x0C\x04'
        self.strings_byte_code = b'\x00\x00\x82\x02'
        
        json_file = open('../Data/NDX/Misc/hashes.json', 'r')
        self.hashes = json.load(json_file)
        self.extract_names = True
        
    def make_Dirs(self):
        
        base_path = "../Data/NDX/All/"
        self.mkdir(base_path)
        self.mkdir(base_path+'battle')
        self.mkdir(base_path+'battle/character')
        self.mkdir(base_path+'battle/charsnd')
        self.mkdir(base_path+'battle/data')
        self.mkdir(base_path+'battle/effect')
        self.mkdir(base_path+'battle/event')
        self.mkdir(base_path+'battle/gui')
        self.mkdir(base_path+'battle/map')
        self.mkdir(base_path+'battle/resident')
        self.mkdir(base_path+'battle/tutorial')
        self.mkdir(base_path+'chat')
        self.mkdir(base_path+'gim')
        self.mkdir(base_path+'map')
        self.mkdir(base_path+'map/data')
        self.mkdir(base_path+'map/pack')
        self.mkdir(base_path+'movie')
        self.mkdir(base_path+'snd')
        self.mkdir(base_path+'snd/init')
        self.mkdir(base_path+'snd/se3')
        self.mkdir(base_path+'snd/se3/map_mus')
        self.mkdir(base_path+'snd/strpck')
        self.mkdir(base_path+'sysdata')
        
        
    def bytes_to_text_TOPX(self, fileRead, offset=-1, end_strings = b"\x00"):
    
        finalText = ''
        TAGS = self.jsonTblTags['TAGS']
        
        if (offset > 0):
            fileRead.seek(offset, 0)
        
        pos = fileRead.tell()
        b = fileRead.read(2)
        while_condition = b''
        while while_condition != b'\x00\x00':
            #print(hex(fileRead.tell()))
            b = ord(b)
            
            if (b >= 0x99 and b <= 0x9F) or (b >= 0xE0 and b <= 0xEB):
                c = (b << 8) + ord(fileRead.read(1))
               
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
                b2 = struct.unpack("<L", fileRead.read(4))[0]
                if b in TAGS:
                    tag_name = TAGS.get(b)
                    
                    tag_param = None
                    tag_search = tag_name.upper()+'S'
                    if (tag_search in self.jsonTblTags.keys()):
                        tags2 = self.jsonTblTags[tag_search]
                        tag_param = tags2.get(b2, None) 
                    if tag_param != None:
                        finalText += tag_param
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
                    
                    next_b = fileRead.read(1)
                    finalText += "{%02X}" % ord(next_b)
                    #if next_b != b'':
                    
                    #else:
                    #    next_b = b"\x80"
            elif b == 0x81:
                next_b = fileRead.read(1)
                if next_b == b"\x40":
                    finalText += "　"
                else:
                    finalText += "{%02X}" % b
                    finalText += "{%02X}" % ord(next_b)
            else:
                finalText += "{%02X}" % b
            b = fileRead.read(2)
            
       
        end = fileRead.tell()
        size = fileRead.tell() - pos - 1
        fileRead.seek(pos)
        hex_string = fileRead.read(size).hex()
        hex_values = ' '.join(a+b for a,b in zip(hex_string[::2], hex_string[1::2]))
        fileRead.seek(end)
        return finalText, hex_values
    
    
    def extract_Files(self, input_file, size, filename):
        hash_name = filename
        if filename in self.hashes.keys():
            hash_name = self.hashes[filename]

        data = input_file.read(size)
        base_path = '../Data/NDX/All/'
        if self.extract_names:
            try:
                output_file = open(base_path + hash_name, 'wb')
            except:
                output_file = open(base_path + filename, 'wb')
        else:
            output_file = open(base_path + filename, 'wb')
        output_file.write(data)
        output_file.close()
    
    def extract_All_Pak3(self):
        
        
        #Story 
        story_pak3 = [self.story_Path+"New/"+ele for ele in os.listdir(self.story_Path+"New")]
        res = [ self.pakComposer_Comptoe(ele, "-d", "-3", False) for ele in story_pak3]
       
    def extract_FPS4(self):
        
        print("potato")
        self.fps4_action("-d", "../Data/NDX/All/battle/data/bt_data.b", "../Data/NDX/All/battle/data/bt_data_battle.dat", "../Data/NDX/Menu/New")
    
    def extract_All_Cab(self):
        
        menuCab = {}
        menuCab['File'] = []
        
        event_path_extract = "../Data/NDX/All\map"
        skits_path_extract = "../Data/NDX/All\chat"
        story_path_extract = "../Data/NDX/All\map\pack"
        path_exceptions = [event_path_extract, skits_path_extract, story_path_extract, "../Data/NDX/All"]
        
        
        for path, subdirs, files in os.walk("../Data/NDX/All"):
            print(path)
            if path not in path_exceptions:
                for name in files:
                    with open(os.path.join(path,name), "rb") as f:
                        data =f.read()
                        
                    if data[:4] == b'MSCF':
                        file_name = name.split(".")[0]
                        self.extract_Cab( os.path.join(path, name), "../Data/NDX/Menu/New/{}.bin".format(file_name))
                    
              
        #Events   
        events_files = [file for file in os.listdir(event_path_extract) if ".bin" in file]
        print(events_files)
        for file in events_files:
            new_file_name = self.events_Path + 'New/{}'.format(file)
            self.extract_Cab( os.path.join(event_path_extract,file), new_file_name)
        
        #Skits       
        skits_files = [file for file in os.listdir(skits_path_extract) if ".bin" in file]
        for file in skits_files:
            new_file_name = self.skits_Path+'New/{}.pak3'.format(self.get_file_name(file))
            self.extract_Cab(os.path.join(skits_path_extract,file), new_file_name)
        
        #Story        
        story_files = [file for file in os.listdir(story_path_extract) if ".bin" in file]
        for file in story_files:
            new_file_name = self.story_Path +'New/{}.bin'.format(file_name)
            self.extract_Cab(os.path.join(story_path_extract,file), new_file_name)
        
    def extract_Main_Archive(self):
        
        print("...Unpacking all.dat")
        shutil.rmtree("../Data/NDX/All")
        self.make_Dirs()
        order = {}
        order['order'] = []
        order_json = open('../Data/NDX/Misc/order.json', 'w')
        eboot = open(self.elf_Original, 'rb')
        eboot.seek(self.POINTERS_BEGIN)
        
        with open(self.allDat_Original, 'rb') as all_dat_file:
            while True:
                file_info = struct.unpack('<3I', eboot.read(12))
                if(file_info[2] == 0):
                    break
                hash_ = "%08X" % file_info[2]

                all_dat_file.seek(file_info[0])
                self.extract_Files(all_dat_file, file_info[1], hash_)
                order['order'].append(hash_)
            json.dump(order, order_json, indent = 4)
            order_json.close()
        
        
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

    def build_Struct_Entry(self, storyFile, f, structDict, baseOffset, blockSize, root):
    
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
            
            f.seek(personAdd)
            print("Offset : {}".format(hex(personAdd)))
            personText, person_hex       = self.bytes_to_text(f)  
            
            print(personText)
            
            #personText = self.extractText(f, personAdd, textAdd - personAdd - 1, tbl)
            
            #unknown1Text     = self.extractText(f, unknown1Add, unknown2Add - unknown1Add - 1, tbl)
            #unknown2Text     = self.extractText(f, unknown2Add, structValueOffset + baseOffset - unknown2Add - 1, tbl)
            
            #Add all the nodes to the base Struct Node        
            structNode = etree.SubElement(root, "Struct")
            etree.SubElement(structNode, "PointerOffset").text = str(structOffset)
            etree.SubElement(structNode, "PointerUnknownValue").text = str(pointer)
            #etree.SubElement(structNode, "Unknown1Text").text = unknown1Text
            #etree.SubElement(structNode, "Unknown2Text").text = unknown2Text
            etree.SubElement(structNode, "TextOffset").text = str(personAdd)
            etree.SubElement(structNode, "PersonJapaneseText").text = personText
            etree.SubElement(structNode, "PersonEnglishText").text = "";
            
            
            #Extract each bubble of text and add it to the EntryList Node
            #entryListNode = etree.SubElement(structNode, "EntryList")
            
            
            #japText         = extractText(f, textAdd, unknown1Add - textAdd - 1, tbl)
            #listVoiceId     = re.findall("\((\w+)\)", japText)
            
            #if len(listVoiceId) > 0:
            #    etree.SubElement(structNode, "Type").text = "VoiceId"
            #else:
            #    etree.SubElement(structNode, "Type").text = "NoVoiceId"
                
            
            #addEntry(japText, structNode, listVoiceId)
            
    
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
        
