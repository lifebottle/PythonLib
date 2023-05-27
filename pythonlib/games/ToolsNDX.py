from .ToolsTales import ToolsTales
import subprocess
# from dicttoxml import dicttoxml
import json
import struct
import shutil
import os
import re
import io
import pandas as pd
import xml.etree.ElementTree as ET
import glob
import lxml.etree as etree
from xml.dom import minidom
from pathlib import Path
class ToolsNDX(ToolsTales):
    
    def __init__(self, tbl):
        
        super().__init__("NDX", tbl, "Narikiri-Dungeon-X")
        
        with open("../{}/Data/{}/Misc/{}".format(self.repo_name, self.gameName, self.tblFile), encoding="utf-8") as f:
                       
            self.jsonTblTags = json.load(f)     
            self.jsonTblTags["TBL"] = { int(k):v for k,v in self.jsonTblTags["TBL"].items()}
            self.jsonTblTags["COLOR"] = { int(k):v for k,v in self.jsonTblTags["COLOR"].items()}
            keys = [int(ele, 16) for ele in self.jsonTblTags["TAGS"].keys()]
            self.jsonTblTags["TAGS"] = dict(zip(keys, list(self.jsonTblTags["TAGS"].values())))
      
            
        self.itable = dict([[i, struct.pack(">H", int(j))] for j, i in self.jsonTblTags['TBL'].items()])
        self.itags = dict([[i, j] for j, i in self.jsonTblTags['TAGS'].items()])
        
        if "COLOR" in self.jsonTblTags.keys():
            self.icolors = dict([[i, j] for j, i in self.jsonTblTags['COLOR'].items()])
        
        
        self.id = 1
        self.struct_id = 1
        self.eboot_name = 'EBOOT.BIN'
        
        
        
        #Load the hash table for the files
        json_file = open('../{}/Data/{}/Misc/hashes.json'.format(self.repo_name, self.gameName), 'r')
        self.hashes = json.load(json_file)
        json_file.close()
        
        self.repo_name          = 'Narikiri-Dungeon-X'
        self.misc               = '../Data/{}/Misc'.format(self.repo_name)
        self.disc_path          = '../Data/{}/Disc'.format(self.repo_name)
        self.story_XML_extract  = '../Data/{}/Story/'.format(self.repo_name)                       #Files are the result of PAKCOMPOSER + Comptoe here
        self.story_XML_new      = '../{}/Data/NDX/Story/XML'.format(self.repo_name)
        self.skit_extract       = '../Data/{}/Skit/'.format(self.repo_name)                                      #Files are the result of PAKCOMPOSER + Comptoe here
        self.elf_new            = '../Data/{}/Disc/New/PSP_GAME/SYSDIR/EBOOT.bin'.format(self.repo_name)
        self.all_extract      = '../Data/{}/All/'.format(self.repo_name)
        self.all_original     = '../Data/{}/Disc/Original/PSP_GAME/USRDIR/all.dat'.format(self.repo_name)
        self.all_new          = '../Data/{}/Disc/New/PSP_GAME/USRDIR/all.dat'.format(self.repo_name)                  #File is all.dat
        self.story_struct_byte_code = b'\x18\x00\x0C\x04'
        self.story_string_byte_code = b'\x00\x00\x82\x02'
        
        self.make_dirs()
    #############################
    #
    # Extraction of files and unpacking
    #
    #############################
    
    # Make the basic directories for extracting all.dat
    def make_dirs(self):
        self.mkdir('../Data')
        self.mkdir('../Data/{}'.format(self.repo_name))
        self.mkdir('../Data/{}/Disc'.format(self.repo_name))
        self.mkdir('../Data/{}/Disc/Original'.format(self.repo_name))
        self.mkdir('../Data/{}/Disc/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Misc'.format(self.repo_name))
        self.mkdir('../Data/{}/All'.format(self.repo_name))
        self.mkdir('../Data/{}/Story'.format(self.repo_name))
        self.mkdir('../Data/{}/Story/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Story/XML'.format(self.repo_name))
        self.mkdir('../Data/{}/Events'.format(self.repo_name))
        self.mkdir('../Data/{}/Events/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Events/XML'.format(self.repo_name))
        self.mkdir('../Data/{}/Menu'.format(self.repo_name))
        self.mkdir('../Data/{}/Menu/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Menu/XML'.format(self.repo_name))
        self.mkdir('../Data/{}/Skits'.format(self.repo_name))
        self.mkdir('../Data/{}/Skits/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Skits/XML'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/character'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/charsnd'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/data'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/effect'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/event'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/gui'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/map'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/resident'.format(self.repo_name))
        self.mkdir('../Data/{}/All/battle/tutorial'.format(self.repo_name))
        self.mkdir('../Data/{}/All/chat'.format(self.repo_name))
        self.mkdir('../Data/{}/All/gim'.format(self.repo_name))
        self.mkdir('../Data/{}/All/map'.format(self.repo_name))
        self.mkdir('../Data/{}/All/map/data'.format(self.repo_name))
        self.mkdir('../Data/{}/All/map/pack'.format(self.repo_name))
        self.mkdir('../Data/{}/All/movie'.format(self.repo_name))
        self.mkdir('../Data/{}/All/snd'.format(self.repo_name))
        self.mkdir('../Data/{}/All/snd/init'.format(self.repo_name))
        self.mkdir('../Data/{}/All/snd/se3'.format(self.repo_name))
        self.mkdir('../Data/{}/All/snd/se3/map_mus'.format(self.repo_name))
        self.mkdir('../Data/{}/All/snd/strpck'.format(self.repo_name))
        self.mkdir('../Data/{}/All/sysdata'.format(self.repo_name))
    
    # Extract the story files
    def extract_All_Story(self, replace=False, extract_XML = True):
        
        print("Extracting Story")
        path = os.path.join( self.all_extract, 'map/pack/')
        
        for f in os.listdir( path ):
            if os.path.isfile( path+f) and '.cab' in f:
                if extract_XML:
                    self.extract_CAB_File(path,f, '../Data/{}/Story'.format(self.repo_name))
                else:
                    self.extract_CAB_File(path,f)
                         
    def extract_CAB_File(self, path, f, xml_path=None):
        
        #Unpack the CAB into PAK3 file
        path_new = '{}/New'.format(xml_path)
        shutil.copy( path+f,os.path.join(path_new, f))
        self.extract_Cab(f, f.replace(".cab", ".pak3"), path_new)

        #Decompress using PAKCOMPOSER + Comptoe
        self.pakComposer_Comptoe(f.replace(".cab", ".dat"), "-d", "-3",0, os.path.join( path_new, f.replace(".cab","")) )       
        
        if xml_path != None:
            #Extract from XML
            self.extract_TSS_File(os.path.join(path_new, f.replace(".cab", ""), f.replace(".cab", "")), xml_path)
            
            
            
    # Extract one single CAB file to the XML format
    def extract_TSS_File(self, pak3_folder, xml_path):
        

        self.id = 1
        self.speaker_id = 1
        self.struct_id = 1
            
        
        if os.path.exists(pak3_folder):
            #1) Grab TSS file from PAK3 folder
            tss, file_tss = self.get_tss_from_pak3(  pak3_folder)
     
            #2) Extract TSS to XML
            self.extract_tss_XML(tss, pak3_folder, xml_path)
        
    def get_tss_from_pak3(self, pak3_folder):
          
        
        if os.path.isdir(pak3_folder):
            folder_name = os.path.basename(pak3_folder)
          
            file_list = [os.path.dirname(pak3_folder) + "/" + folder_name + "/" + ele for ele in os.listdir(pak3_folder)]
            
            for file in file_list:
                with open(file, "rb") as f:
                    data = f.read()
                  
                    if data[0:3] == b'TSS':
                        print("... Extract TSS for file {} of size: {}".format(folder_name, len(data)))
                        return io.BytesIO(data), file
    
    def extract_All_Event(self):
        
        print("Extracting Events")
        events_files = [file for file in os.listdir("../Data/{}/All/map".format(self.repo_name)) if file.endswith(".bin")]
        for event_file in events_files:
            self.extract_Event_File(event_file)
            
        #Extract Field file
        
    def extract_Field(self):
        
        
        with open('../Data/{}/Events/New/map/field/field.dat'.format(self.repo_name), "rb") as f:
            data = f.read()
            tss_offset = struct.unpack("<I",data[0x94:0x98])[0]
            print(hex(tss_offset))
            print(hex(len(data)))
            tss = io.BytesIO(data[tss_offset:])
            with open("../test.bin", "wb") as f:
                f.write(data[tss_offset:])
            self.extract_tss_XML(tss, "field.bin", '../Data/{}/Events'.format(self.repo_name))
            
    def extract_Event_File(self, event_file):
        
        self.id = 1
        self.speaker_id = 1
        self.struct_id = 1
        
        #1) Extract CAB to folder
        event_path = '../Data/{}/Events/New/map'.format(self.repo_name)
        self.extract_Cab(event_file, event_file, event_path)
        
        #2) Grab TSS file from the decompressed CAB file
        tss, file_tss = self.get_tss_from_event(  os.path.join(event_path, event_file.replace(".bin",""), event_file.replace(".bin",".dat")))
 
        #3) Extract TSS to XML
        self.extract_tss_XML(tss, event_file, '../Data/{}/Events'.format(self.repo_name))
        return tss
        
    def get_tss_from_event(self, event_file):
        
        with open(event_file, "rb") as event_f:
            data = event_f.read()
            file_offset = struct.unpack("<I", data[0x6C:0x70])[0]
            tss_data = data[file_offset:len(data)]
            dirname = os.path.dirname(event_file)
            self.mkdir( os.path.join(dirname, "TSS"))
            file_tss = os.path.join(dirname, "TSS", os.path.basename(event_file).replace(".dat",".tss"))
            with open(file_tss, "wb") as f:
                f.write(tss_data)
            
            return io.BytesIO(tss_data), file_tss
                   
    def extract_tss_XML(self, tss, cab_file_name, xml_path):
        
        root = etree.Element('SceneText')
   
        tss.seek(0)
        tss.read(12)
        strings_offset = struct.unpack('<I', tss.read(4))[0]     
        tss.read(4)
        pointer_block_size = struct.unpack('<I', tss.read(4))[0]
        block_size = struct.unpack('<I', tss.read(4))[0]
        
        #Create all the Nodes for Struct
        speaker_node = etree.SubElement(root, 'Speakers')
        etree.SubElement(speaker_node, 'Section').text = "Speaker"   
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = "Story"       
        
        
        texts_offset, pointers_offset = self.extract_Story_Pointers(tss, self.story_struct_byte_code, strings_offset, pointer_block_size)
        person_offset = [ self.extract_From_Struct(tss, strings_offset, pointer_offset, struct_offset, root) for pointer_offset, struct_offset in zip(pointers_offset, texts_offset)]


        #Create all the Nodes for Strings and grab the minimum offset
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = "Other Strings"
        tss.seek(16)
        texts_offset, pointers_offset = self.extract_Story_Pointers(tss, self.story_string_byte_code, strings_offset, pointer_block_size)
        [ self.extract_From_String(tss, strings_offset, pointer_offset, text_offset, strings_node) for pointer_offset, text_offset in zip(pointers_offset, texts_offset)]
        
        text_start = min( min(person_offset, default=0), min(texts_offset, default=0))
  
        #Write the XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
        xml_path = os.path.join(xml_path,"XML", self.get_file_name(cab_file_name)+".xml")
        with open(xml_path, "wb") as xmlFile:
            xmlFile.write(txt)
    
    
    def extract_Debug_XML(self):
        
        root = etree.Element('SceneText')
        self.speaker_id = 1
        
        with open(r"G:\TalesHacking\TOP_Narikiri\BD3BDFF5\ar.dat", "rb") as tss:
            strings_offset = 0x1EF130 
            pointer_block_size = 0x1EF4A0
    
            #Create all the Nodes for Struct
            speaker_node = etree.SubElement(root, 'Speakers')
            etree.SubElement(speaker_node, 'Section').text = "Speaker"
            strings_node = etree.SubElement(root, 'Strings')
            etree.SubElement(strings_node, 'Section').text = "Story"       
            
            
            texts_offset, pointers_offset = self.extract_Story_Pointers(tss, self.story_struct_byte_code, strings_offset, pointer_block_size)
            person_offset = [ self.extract_From_Struct(tss, strings_offset, pointer_offset, struct_offset, root) for pointer_offset, struct_offset in zip(pointers_offset, texts_offset)]

            #Create all the Nodes for Strings and grab the minimum offset
            strings_node = etree.SubElement(root, 'Strings')
            etree.SubElement(strings_node, 'Section').text = "Other Strings"
            tss.seek(16)
            texts_offset, pointers_offset = self.extract_Story_Pointers(tss, self.story_string_byte_code, strings_offset, pointer_block_size)
            [ self.extract_From_String(tss, strings_offset, pointer_offset, text_offset, strings_node) for pointer_offset, text_offset in zip(pointers_offset, texts_offset)]
            
            text_start = min( min(person_offset, default=0), min(texts_offset, default=0))

            etree.SubElement(root, "TextStart").text = str(text_start)
      
            #Write the XML file
            txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
            with open(r'G:\TalesHacking\TOP_Narikiri\BD3BDFF5\debug.xml', "wb") as xmlFile:
                xmlFile.write(txt)
    def extract_From_Struct(self, f,strings_offset, pointer_offset, struct_offset, root):
         
        #print("Offset: {}".format(hex(struct_offset)))
        f.seek(struct_offset, 0)
        
        #Extract all the information and create the entry
        f.read(4)
        unknown_pointer  = struct.unpack('<I', f.read(4))[0]
        speaker_offset   = struct.unpack('<I', f.read(4))[0] + strings_offset
        text_offset      = struct.unpack('<I', f.read(4))[0] + strings_offset   
        speaker_text   = self.bytes_to_text(f, speaker_offset)[0]
        
        if speaker_text != None:
            struct_speaker_id     = self.add_Speaker_Entry(root.find("Speakers"), pointer_offset, speaker_text)      
        japText         = self.bytes_to_text(f, text_offset)[0]
        jap_split_bubble = japText.split("<Bubble>")       
        [self.create_Entry(root.find("Strings"), pointer_offset, jap,1, "Struct", struct_speaker_id, unknown_pointer) for jap in jap_split_bubble]
        self.struct_id += 1
        
        return speaker_offset
    
    def add_Speaker_Entry(self, root, pointer_offset, japText):
        
        speaker_entries = [entry for entry in root.iter("Entry") if entry != None and entry.find("JapaneseText").text == japText]
        struct_speaker_id = 0
        
        if len(speaker_entries) > 0:
            
            #Speaker already exist
            speaker_entries[0].find("PointerOffset").text = speaker_entries[0].find("PointerOffset").text + ",{}".format(pointer_offset)
            struct_speaker_id = speaker_entries[0].find("Id").text
            
        else:
            
            #Need to create that new speaker
            entry_node = etree.SubElement(root, "Entry")
            etree.SubElement(entry_node,"PointerOffset").text = str(pointer_offset)
            etree.SubElement(entry_node,"JapaneseText").text  = str(japText)
            etree.SubElement(entry_node,"EnglishText")
            etree.SubElement(entry_node,"Notes")
            etree.SubElement(entry_node,"Id").text            = str(self.speaker_id)
            etree.SubElement(entry_node,"Status").text         = "To Do"
            struct_speaker_id = self.speaker_id
            self.speaker_id += 1
              
        return struct_speaker_id
    
    def extract_From_String(self, f, strings_offset, pointer_offset, text_offset, root):
        
        
        f.seek(text_offset, 0)
        japText = self.bytes_to_text(f, text_offset)[0]
        self.create_Entry(root, pointer_offset, japText,1, "Other Strings", -1, "")
    
    def extract_Story_Pointers(self, f, bytecode, strings_offset, pointer_block_size):

        read = 0
        text_offset = []
        pointer_offset = []
        while read < pointer_block_size:
            b = f.read(4)
            if b == bytecode:
                
                pointer_offset.append(f.tell())
                text_offset.append(struct.unpack('<I', f.read(4))[0] + strings_offset)
                read += 4
            else:
                read += 4
        
        return text_offset, pointer_offset
    
    #def create_Struct_Entry(self, strings_node, pointer_offset, text, speaker_id = -1):
        
    #start_offset : where the pointers start for the section
    # nb_per_block : number of pointers per block before adding step
    # step : number of bytes before the next block
    def get_special_pointers(self, text_start, text_max, base_offset, start_offset, nb_per_block, step, section,file_path=''):
         
        if file_path == '':
            file_path = '../Data/{}/Misc/{}'.format(self.repo_name, self.eboot_name)
        
        f = open(file_path , "rb")  
        f.seek(start_offset, 0)
        pointers_offset = []
        pointers_value  = []
        list_test = []
        is_bad_count = 0
        
        while is_bad_count <2:
            block_pointers_offset = [f.tell()+4*i for i in range(nb_per_block)]
            
            block_pointers_value = struct.unpack(f"<{nb_per_block}L", f.read(4 * nb_per_block))
            list_test.extend(block_pointers_value)         
            
            for i in range(len(block_pointers_offset)):
                if (block_pointers_value[i] + base_offset >= text_start and block_pointers_value[i] + base_offset <= text_max):
                    pointers_offset.append(block_pointers_offset[i])
                    pointers_value.append(block_pointers_value[i])
                    is_bad_count = 0

                elif block_pointers_value[i] != 0:
                    is_bad_count += 1
            f.read(step)
        f.close()
        
        #Only grab the good pointers
        good_indexes = [index for index,ele in enumerate(pointers_value) if ele != 0]   
        pointers_offset = [pointers_offset[i] for i in good_indexes]
        pointers_value = [pointers_value[i] for i in good_indexes]

        return [pointers_offset, pointers_value]
    
    
    
    
    def get_Direct_Pointers(self, text_start, text_max, base_offset, pointers_list, section,file_path=''):
         
        if file_path == '':
            file_path = '../Data/{}/Misc/{}'.format(self.repo_name, self.eboot_name)
        
        f = open(file_path , "rb")  
        pointers_offset = []
        pointers_value  = []
        
        for pointer in pointers_list:
            f.seek(pointer, 0)
            value = struct.unpack("<I", f.read(4))[0]      
            if ((value + base_offset >= text_start) and (value + base_offset <= text_max)):
                pointers_offset.append(pointer)
                pointers_value.append(value)
        f.close()
        
        #Only grab the good pointers
        good_indexes = [index for index,ele in enumerate(pointers_value) if ele != 0]   
        pointers_offset = [pointers_offset[i] for i in good_indexes]
        pointers_value = [pointers_value[i] for i in good_indexes]

        return [pointers_offset, pointers_value]
    
 
    def create_Entry(self, strings_node, pointer_offset, text, to_translate, entry_type, speaker_id, unknown_pointer):
        
        #Add it to the XML node
        entry_node = etree.SubElement(strings_node, "Entry")
        etree.SubElement(entry_node,"PointerOffset").text = str(pointer_offset)
        text_split = re.split(self.COMMON_TAG, text)
        
        if len(text_split) > 1 and any(possible_value in text for possible_value in self.VALID_VOICEID):
            etree.SubElement(entry_node,"VoiceId").text  = text_split[1]
            etree.SubElement(entry_node, "JapaneseText").text = ''.join(text_split[2:])
        else:
            etree.SubElement(entry_node, "JapaneseText").text = text
            
        eng_text = ''
            
        etree.SubElement(entry_node,"EnglishText")
        etree.SubElement(entry_node,"Notes")
        etree.SubElement(entry_node,"Id").text            = str(self.id)   
        statusText = "To Do"
        
        if entry_type == "Struct":
            etree.SubElement(entry_node,"StructId").text      = str(self.struct_id)
            etree.SubElement(entry_node,"SpeakerId").text     = str(speaker_id)
            etree.SubElement(entry_node,"UnknownPointer").text = str(unknown_pointer)
                      
        etree.SubElement(entry_node,"Status").text        = statusText      
        self.id += 1
        
        
    def create_Node_XML(self, fileName, list_informations, parent):
        
        root = etree.Element(parent)
        sections = list(set([s for s, pointers_offset, text, to_translate in list_informations]))
        
        for section in sections:    
            strings_node = etree.SubElement(root, 'Strings')
            etree.SubElement(strings_node, 'Section').text = section
            list_informations_filtered = [(s, pointers_offset, text, to_translate) for s, pointers_offset, text, to_translate in list_informations if s == section]
            
            for s, pointers_offset, text, to_translate in list_informations_filtered:
                self.create_Entry( strings_node,  pointers_offset, text, to_translate, "Menu", -1, -1)
         
        return root
     
    def get_Starting_Offset(self, root, tss, base_offset):
       
        #String Pointers
        strings_pointers = [int(ele.find("PointerOffset").text) for ele in root.findall('Strings[Section="Other Strings"]/Entry')]
        strings_offset = []
        structs_offset = []

        for pointer_offset in strings_pointers:
            tss.seek(pointer_offset)
            strings_offset.append( struct.unpack("<I", tss.read(4))[0] + base_offset)
        
        #Struct Pointers
        struct_pointers =  [int(ele.find("PointerOffset").text) for ele in root.findall('Strings[Section="Story"]/Entry')]
        for pointer_offset in struct_pointers:
            tss.seek(pointer_offset)
            struct_offset = struct.unpack("<I", tss.read(4))[0] + base_offset 
            tss.seek(struct_offset)
            tss.read(8)
            struct_offset = struct.unpack("<I",tss.read(4))[0] + base_offset
            structs_offset.append(struct_offset)
         
        struct_count = len(structs_offset)
        strings_count = len(strings_offset)
        
        if struct_count == 0:
            return min(strings_offset)
        elif strings_count == 0:
            return min(structs_offset)
        else:
            return min( min(structs_offset), min(strings_offset))
         
    def insert_Speaker(self, root, tss, base_offset):
        
        speaker_dict = dict()
        
        for speaker_node in root.findall("Speakers/Entry"):          
            bytes_entry = self.get_node_bytes(speaker_node)
            speaker_id  = speaker_node.find("Id").text
            speaker_dict[speaker_id] = struct.pack("<I", tss.tell() - base_offset)
            tss.write(bytes_entry)
            tss.write(b'\x00')
        return speaker_dict
    
    #Repack SCPK files for Story
    def pack_Story_File(self, story_ep_no):
        
        
        #Grab the Tss file inside the folder
        story_path = '../Data/{}/Story/'.format(self.repo_name)
        tss, file_tss = self.get_tss_from_pak3( story_path + 'New/{}/{}'.format(story_ep_no, story_ep_no) )
        
        tss.read(12)
        base_offset = struct.unpack('<I', tss.read(4))[0]
        tree = etree.parse('../{}/Data/{}/Story/XML/{}'.format(self.repo_name, self.gameName,story_ep_no+'.xml'))
        root = tree.getroot()
        
        #Move to the start of the text section
        start_offset = self.get_Starting_Offset(root, tss, base_offset)
        tss.seek(start_offset,0)

        #Insert all Speaker Nodes from Struct
        speaker_dict = self.insert_Speaker(root, tss, base_offset)
        
        #Do stuff for Struct
        struct_dict = dict()
        struct_entries = root.findall('Strings[Section="Story"]/Entry')
        
        struct_ids = list(set([int(entry.find("StructId").text) for entry in struct_entries]))
        for struct_id in struct_ids:
            
            entries = [entry for entry in struct_entries if int(entry.find("StructId").text) == struct_id]        
            text_offset = tss.tell()
            
            bytes_text = b''
            for struct_node in entries:
                
                voice_id = struct_node.find("VoiceId")
                if voice_id != None:
                    voice_final = voice_id.text.replace('<','(').replace('>',')')
                    tss.write(b'\x09')
                    tss.write( self.text_to_bytes(voice_final))
                    
                
                    bytes_text = self.get_node_bytes(struct_node)
                    tss.write(bytes_text)
                    tss.write(b'\x0C')
            
            tss.seek(tss.tell()-1)
            tss.write(b'\x00\x00\x00')    
            
            
            #Construct Struct
            struct_dict[ int(struct_node.find("PointerOffset").text)] = struct.pack( "<I", tss.tell() - base_offset)
            tss.write(struct.pack("<I", 1))
            tss.write(struct.pack("<I", int(struct_node.find("UnknownPointer").text)))      #UnknownPointer
            tss.write(speaker_dict[struct_node.find("SpeakerId").text])                     #PersonPointer
            tss.write(struct.pack("<I", text_offset - base_offset))                         #TextPointer
            tss.write(struct.pack("<I", text_offset + len(bytes_text) + 1 - base_offset))
            tss.write(struct.pack("<I", text_offset + len(bytes_text) + 2 - base_offset))
            tss.write(b'\x00')
    
        #Do Other Strings
        string_dict = dict()
        for string_node in root.findall('Strings[Section="Other Strings"]/Entry'):
            string_dict[ int(string_node.find("PointerOffset").text)] = struct.pack("<I", tss.tell() - base_offset)
            bytes_text = self.get_node_bytes(string_node)
            tss.write(bytes_text)
            tss.write(b'\x00')
            
        #Update Struct pointers
        for pointer_offset, value in struct_dict.items():
            tss.seek(pointer_offset)
            tss.write(value)
            
        #Update String pointers
        for pointer_offset, value in string_dict.items():
            tss.seek(pointer_offset)
            tss.write(value)
        
            
        with open(file_tss, "wb") as f:
            f.write(tss.getvalue())
            
        #PAK3
        self.pakComposer_Comptoe(story_ep_no, "-c", "-3", 0, story_path + 'New/{}'.format(story_ep_no))
        os.remove(story_path + 'New/{}/{}.dat'.format(story_ep_no, story_ep_no))
        os.rename(story_path + 'New/{}/{}.pak3'.format(story_ep_no, story_ep_no), story_path + 'New/{}/{}.dat'.format(story_ep_no, story_ep_no))
        self.adjust_pak3(story_path + 'New/{}/{}.dat'.format(story_ep_no, story_ep_no))
        
        #CAB
        self.make_Cab('{}/{}.dat'.format(story_ep_no, story_ep_no), story_ep_no+".cab", story_path+'New')
        return tss.getvalue()
        
    def unpack_Folder(self, folder_path):
        
        files = [folder_path+ '/' + ele for ele in os.listdir(folder_path) if os.path.isdir(folder_path+ '/' + ele) == False]
        
        for file in files:
            
            with open(file, 'rb') as f:
                file_data = f.read(12)
                extension = self.get_extension(file_data)
                folder_name = os.path.basename(file).split(".")[0].upper()
                
                #Unpack FPS4
                if extension == 'fps4':
                    self.fps4_action('-d', file, folder_path)
                    self.unpack_Folder( os.path.join( folder_path, folder_name))
                    
                #Unpack CAB
                if extension== 'cab' and '.dat' not in file:
                    
                    #print('cab')
                    folder_name = os.path.basename(file).split(".")[0].upper()
                    #print('Destination {}'.format(os.path.join(folder_path, folder_name, os.path.basename(file))))
                    self.extract_Cab(file, file, folder_path)
            
    def prepare_Menu_File(self, hashes_folder):
        
        menu_file_path = "../Data/{}/Menu/New/{}".format(self.repo_name, hashes_folder)
        for filename in os.listdir(menu_file_path):
            
            if os.path.isdir(filename):
                shutil.rmtree(filename)
                
        self.unpack_Folder( menu_file_path)
        
                
    def extract_all_menu(self):
        
        res = [self.prepare_Menu_File(ele) for ele in list(set([ele['Hashes_Name'] for ele in self.menu_files_json if ele['Hashes_Name'] != '']))]
        
        print("Extracting Menu Files")
        self.mkdir("../Data/{}/Menu/New".format(self.repo_name))
        
        for file_definition in self.menu_files_json:
           
            #if file_definition['Hashes_Name'] != '':
            #    self.prepare_Menu_File(file_definition['Hashes_Name'])
                                   
            self.extract_menu_file(file_definition)
            
    def extract_menu_file(self, file_definition):
        
        
        section_list = []
        pointers_offset_list = []
        texts_list = []
        to_translate = []

        self.prepare_Menu_File(file_definition['Hashes_Name'])
        
        base_offset = file_definition['Base_Offset']
        file_path   = file_definition['File_Extract']
        with open(file_path, "rb") as f:

            for section in file_definition['Sections']:
                
        
                text_start = section['Text_Start']
                text_end = section['Text_End'] 
                  
                #Extract Pointers of the file
                print("Section: {}".format(section['Section']))
                pointers_offset = section['Pointer_Offset_Start']
                if isinstance(pointers_offset, list):
                    pointers_offset, pointers_value = self.get_Direct_Pointers(text_start, text_end, base_offset, pointers_offset, section,file_path)
                else:
                    pointers_offset, pointers_value = self.get_style_pointers( text_start, text_end, base_offset, section['Pointer_Offset_Start'], section['Style'], file_path)
          
              
                #Extract Text from the pointers
                #print([hex(ele + base_offset) for ele in pointers_value])
                texts = [ self.bytes_to_text(f, ele + base_offset)[0] for ele in pointers_value]
                
                #Make a list
                section_list.extend( [section['Section']] * len(texts)) 
                pointers_offset_list.extend( pointers_offset)
                texts_list.extend( texts )
                to_translate.extend( [section['To_Translate']] * len(texts))
       
        #Remove duplicates
        list_informations = self.remove_duplicates(section_list, pointers_offset_list, texts_list, to_translate)
        df = pd.DataFrame({"PointerOffset":pointers_offset_list, "Text": texts_list}, columns=['PointerOffset', 'Text'])

        #Build the XML Structure with the information
        root = self.create_Node_XML(file_path, list_informations, "MenuText")
        
        #Write to XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
        with open(file_definition['File_XML'].replace("/{}".format(self.repo_name),"").replace("{}".format(self.gameName),self.repo_name), "wb") as xmlFile:
            xmlFile.write(txt)
    
    def remove_duplicates(self, section_list, pointers_offset, texts_list, to_translate_list):
        
        final_list = []
        unique_text = set(texts_list)
        for text in unique_text:
            
            indexes = [index for index,ele in enumerate(texts_list) if ele == text]


            
            found = [str(pointers_offset[i]) for i in indexes]
            found.sort(reverse=False)
            found = list( set(found))
            pointers_found = ",".join(found)
           
            section = [section_list[i] for i in indexes][0]
            to_translate = [to_translate_list[i] for i in indexes][0]
            final_list.append( (section, pointers_found, text, to_translate))
        
        final_list.sort(key=lambda x: int(x[1].split(",")[-1]))

        return final_list
    
    
    def bytes_to_text(self, fileRead, offset=-1, end_strings = b"\x00"):
    
        final_text = ''
        TAGS = self.jsonTblTags['TAGS']
        
        if (offset > 0):
            fileRead.seek(offset, 0)
        
        pos = fileRead.tell()
        b = fileRead.read(1)

        while b != end_strings:
            #print(hex(fileRead.tell()))
            
            b = ord(b)
            
            #Normal character
            if (b >= 0x80 and b <= 0x9F) or (b >= 0xE0 and b <= 0xEA):
                c = (b << 8) + ord(fileRead.read(1))
               
                try:
                    final_text += self.jsonTblTags['TBL'][c]
                except KeyError:
                    b_u = (c >> 8) & 0xff
                    b_l = c & 0xff
                    final_text += ("{%02X}" % b_u)
                    final_text += ("{%02X}" % b_l)
                    
            #Line break
            elif b == 0x0A:
                final_text += ("\n")
                
            elif b == 0x0C:
                final_text += "<Bubble>"
                           
            #Find a possible Color
            elif b == 0x1:
                
                offset_temp = fileRead.tell()
                b2 = struct.unpack("<B", fileRead.read(1))[0]
                if b in TAGS:
                    
                    tag_name = TAGS.get(b)
                    
                    tag_param = None
                    tag_search = tag_name.upper()
                    if (tag_search in self.jsonTblTags.keys()):
                        tags2 = self.jsonTblTags[tag_search]
                        tag_param = tags2.get(b2, None) 
                    if tag_param != None:
                        final_text += tag_param
                    else:
                        #Pad the tag to be even number of characters
                        hex_value = self.hex2(b2)
                        final_text += '<{}:{}>'.format(tag_name, hex_value)
                else:
                    final_text += "<%02X:%08X>" % (b, b2)
            
            #Found an icon
            elif b == 0xB:
                next_bytes = fileRead.read(3)
                final_text += '<icon:{}>'.format( int.from_bytes(next_bytes, 'little'))
                
                
            #Found a name tag
            elif b in [0x4, 0x9]:
                
             
                val=""
                while fileRead.read(1) != b"\x29":
                    fileRead.seek(fileRead.tell()-1)
                    val += fileRead.read(1).decode("cp932")
                val += ')'
                val = val.replace('(','<').replace(')','>')
                
                final_text += val
                
            elif chr(b) in self.PRINTABLE_CHARS:
                final_text += chr(b)
           
            elif b >= 0xA1 and b < 0xE0:
                final_text += struct.pack("B", b).decode("cp932")
                
            b = fileRead.read(1)
            
        return final_text, pos
                

    def text_to_bytes(self, text):
        
        splitLineBreak = text.split('\x0A')
        nb = len(splitLineBreak)
        bytesFinal = b''
        i=0

        for line in splitLineBreak:
            string_hex = re.split(self.HEX_TAG, line)
            string_hex = [sh for sh in string_hex if sh]
            #print(string_hex)
            for s in string_hex:
                if re.match(self.HEX_TAG, s):
                    bytesFinal += struct.pack("B", int(s[1:3], 16))
                else:
                    s_com = re.split(self.COMMON_TAG, s)
                    s_com = [sc for sc in s_com if sc]
                    
                    for c in s_com:
                      
                        if re.match(self.COMMON_TAG, c):
                            if ":" in c:
                                split = c.split(":")
                                tag = split[0][1:]
                                
                                if tag == "icon":
                                    bytesFinal += struct.pack("B", 0xB)
                                    bytesFinal += int(split[1][:-1]).to_bytes(3, 'little')
                                elif tag == "color":
                                    bytesFinal += struct.pack("B", 0x1)
                                    bytesFinal += struct.pack("B", int(split[1][:-1], 16))
                                else:
                                    
                                    bytesFinal += struct.pack("B", int(split[0][1:], 16))
                                    bytesFinal += struct.pack("<I", int(split[1][:8], 16))
                                    
                            if (c in self.jsonTblTags['NAME']):         
                                bytesFinal += struct.pack("B", 0x4)
                                c = c.replace("<","(").replace(">",")")
                                bytesFinal += c.encode("cp932")
                                
                            if "VSM" in c:
                                bytesFinal += struct.pack("B", 0x9)
                                c = c.replace("<","(").replace(">",")")
                                bytesFinal += c.encode("cp932")
                                
                            if c in self.icolors:
                                bytesFinal += struct.pack("B", 0x1)
                                bytesFinal += struct.pack("B", self.icolors[c])
                        else:
                            for c2 in c:
                                if c2 in self.itable.keys():
                                    bytesFinal += self.itable[c2]
                                else:
                                   
                                    bytesFinal += c2.encode("cp932")
           
            i=i+1
            if (nb >=2 and i<nb):
                bytesFinal += b'\x0A'
        
        return bytesFinal    
        

        
        
    
    def extract_All_Skit(self, extract_XML = False):
        
        print("Extracting Skits")
        path = os.path.join( self.all_extract, 'chat/')
        skitsPath ='../Data/Archives/Skits/'
        self.mkdir(skitsPath)
        
        
        for f in os.listdir( path ):
            if os.path.isfile( path+f) and '.cab' in f:
                if extract_XML:
                    self.extract_CAB_File(path,f, '../Data/{}/Skits'.format(self.repo_name))
                else:
                    self.extract_CAB_File(path,f)

                
    # Extract each of the file from the all.dat
    def extract_files(self, start, size, file_name, all_read):

            all_read.seek(start, 0)
            data = all_read.read(size)
            
            with open( os.path.join(self.all_extract, file_name), mode='wb') as output_file:
                output_file.write(data)

    def pack_Menu_Archives(self):
        
        menu_archives = list(set([ (ele['File_Original'], ele['Hashes_Name']) for ele in self.menu_files_json if ele['File_Original'] != ele['File_Extract']]))
        
        for file_original, hashes_name in menu_archives:

            name = os.path.basename(file_original)
            self.pack_Archive('../Data/{}/Menu/New/{}/{}'.format(self.repo_name, hashes_name, name))
            
    def pack_All_Menu(self):
        
        print("Insert Menu Files")
        for ele in self.menu_files_json:
            
            print("Insert {}".format(os.path.basename(ele['File_XML'])))
            self.pack_Menu_File(ele['File_Extract'])
            
            if 'EBOOT' not in ele['File_Extract']:
                
                name = os.path.basename(ele['File_Extract']).split(".")[0]
                self.make_Cab(name +".dat", (name+".cab").upper(), os.path.join(os.path.dirname(ele['File_Extract']),
                                                                                "../.."))
            
        self.pack_Menu_Archives()
        
    def pack_Archive(self, file_path):
         
        path = os.path.dirname(file_path)
        
        #FPS4 Archive
        if '.b' in file_path:   
            list_files = [path +'/' + ele for ele in os.listdir( path) if '.b' not in ele if '.dat' in ele]
            
            self.fps4_action('-c', file_path.replace(".b",""), path)
            [ shutil.copy(file_path.replace(".b",".dat"), ele) for ele in list_files]
            os.remove(file_path.replace(".b",".dat"))
            
            
    # Extract the file all.dat to the different directorties
    def extract_main_archive(self):
        
        #Clean files and folders
        shutil.rmtree("../Data/{}/Menu/New".format(self.repo_name))
        for file in os.scandir("../Data/{}/All".format(self.repo_name)):
            if os.path.isfile(file.path):
                os.remove(file.path,)
        self.mkdir("../Data/{}/All".format(self.repo_name))
        self.mkdir("../Data/{}/Menu/New".format(self.repo_name))
        
        order = {}
        order['order'] = []
        order_json = open( os.path.join( self.misc, 'order.json'), 'w')
        files_to_prepare = [ele['Hashes_Name'] for ele in self.menu_files_json if ele['Hashes_Name'] != '']
        
        #Extract decrypted eboot
        self.extract_Decripted_Eboot()
        
        
        #Open the eboot
        eboot = open( os.path.join( self.misc, self.eboot_name), 'rb')
        eboot.seek(0x1FF624)
        print("Extract All.dat")
        with open(self.all_original, "rb") as all_read:
            while True:
                file_info = struct.unpack('<3I', eboot.read(12))
                if(file_info[2] == 0):
                    break
                hash_ = '%08X' % file_info[2]
                final_name = hash_
                if hash_ in self.hashes.keys():
                    final_name = self.hashes[hash_]
  
                self.extract_files(file_info[0], file_info[1], final_name, all_read)
                
                #Story file
                if final_name.startswith("map/pack/ep_") and final_name.endswith(".cab"):
                    story_dest = "../Data/{}/Story/New/{}".format( self.repo_name, os.path.basename(final_name))
                    os.makedirs(os.path.dirname(story_dest), exist_ok=True)
                    shutil.copy( os.path.join(self.all_extract, final_name), story_dest)
                    
                #Event  file
                elif final_name.startswith("map/") and os.path.dirname(final_name) == "map" and final_name.endswith(".bin"):
                    event_dest = "../Data/{}/Events/New/{}".format( self.repo_name, final_name)
                    os.makedirs(os.path.dirname(event_dest), exist_ok=True)
                    shutil.copy( os.path.join(self.all_extract, final_name), event_dest)
                    
                if len( [ele for ele in files_to_prepare if ele in final_name]) > 0:
                    copy_path = os.path.join("../Data/{}/Menu/New/{}".format(self.repo_name, final_name))
                    Path(os.path.dirname(copy_path)).mkdir(parents=True, exist_ok=True)
                    shutil.copy( os.path.join(self.all_extract, final_name), copy_path)
                
                order['order'].append(hash_)
            json.dump(order, order_json, indent = 4)
            order_json.close()
        
    def pack_Main_Archive(self, debug_room=True):
        addrs = []
        sizes = []
        buffer = 0
        
        print("Updating all.dat archive")
        with open( os.path.join( self.misc, 'order.json'), 'r') as order_file:
            order_hash = json.load(order_file)
   
        elf = open( self.elf_new, 'r+b')
        elf.seek(0x1FF624)
        
        #Menu files to reinsert
        menu_files = [ele['Hashes_Name'] for ele in self.menu_files_json if ele['Hashes_Name'] != '']
        with open(self.all_new , 'wb') as all_file:
            for name in order_hash['order']:
                if name in self.hashes.keys():
                    name = self.hashes[name]
                   
                data = b''
                new_path = ''
                #Menu files to repack
                if os.path.dirname(name) in menu_files:     
                    new_path = '../Data/{}/Menu/New/{}'.format(self.repo_name, name)
      
                #Story files to repack
                elif os.path.basename(name).startswith("ep_"): 
                    #print(name)
                    new_path = '../Data/{}/Story/New/{}'.format(self.repo_name, os.path.basename(name))
                    
                #Events files to repack
                elif os.path.basename(name).startswith("ep_"): 
                    #print(name)
                    new_path = '../Data/{}/Events/New/{}'.format(self.repo_name, os.path.basename(name))
                    
                else:
                    new_path = os.path.join( self.all_extract, name)
                    
                with open( new_path, 'rb') as final_f:
                    
                    data = final_f.read()
  
                        
                        
                size = len(data)
                sizes.append(size)
                remainder = 0x800 - (size % 0x800)
                if remainder == 0x800:
                    remainder = 0
                addrs.append(buffer)
                buffer += size + remainder
                all_file.write(data)
                all_file.write(b'\x00' * remainder)
                
            for i in range(len(sizes)):
                elf.write(struct.pack('<I', addrs[i]))
                elf.write(struct.pack('<I', sizes[i]))
                elf.write(struct.pack('<I', int(order_hash['order'][i], 16)))
                
            if not(debug_room):
                elf.seek(0x1AB3B8)
                elf.write('title'.encode('cp932'))
        elf.close()
        all_file.close()
        
    def adjust_pak3(self, pak3_file): 
        
        pointer_value = []
        with open(pak3_file, "rb") as f:
            data = f.read()
            f.seek(0x4)
            pointer_value = struct.unpack("<3I", f.read(12))
            
        with open(pak3_file, "wb") as f2:
            f2.write(data[:16])
            f2.write(b'\x00' * 48)
            f2.write(data[0x10:])
            
            f2.seek(0x4)
            for p in pointer_value:
                f2.write(struct.pack("<I", p + 0x30))
            
    def extract_Decripted_Eboot(self):
        print("Extracting Eboot")
        args = ["deceboot", "../Data/{}/Disc/Original/PSP_GAME/SYSDIR/EBOOT.BIN".format(self.repo_name), "../Data/{}/Misc/EBOOT.BIN".format(self.repo_name)]
        listFile = subprocess.run(
            args,
            cwd= os.getcwd(),
            )
        
    def pakcomposer(action, file_name, working_directory):
        
        args = [ "pakcomposer", action, os.path.basename(file_name), "-3", "-x", "-u", "-v"]
        listFile = subprocess.run(
            args,
            cwd=working_directory
            )