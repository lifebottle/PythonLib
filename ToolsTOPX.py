from ToolsTales import ToolsTales
import subprocess
from dicttoxml import dicttoxml
import json
import struct
import shutil
import os
import re
import io
import pandas as pd
import xml.etree.ElementTree as ET
import lxml.etree as etree
from xml.dom import minidom
from pathlib import Path
class ToolsTOPX(ToolsTales):
    
    def __init__(self, tbl):
        
        super().__init__("NDX", tbl, "Narikiri-Dungeon-X")
        
        with open("../{}/Data/Misc/{}".format(self.repo_name, self.tblFile), encoding="utf-8") as f:
                       
            jsonRaw = json.load(f)       
            self.jsonTblTags ={ k1:{ int(k2,16) if (k1 not in ["TBL", "NAME"]) else k2:v2 for k2,v2 in jsonRaw[k1].items()} for k1,v1 in jsonRaw.items()}
            
            
        self.itable = dict([[i, struct.pack(">H", int(j))] for j, i in self.jsonTblTags['TBL'].items()])
        self.itags = dict([[i, j] for j, i in self.jsonTblTags['TAGS'].items()])
        if "NAME" in self.jsonTblTags.keys():
            self.inames = dict([[i, j] for j, i in self.jsonTblTags['NAME'].items()])
        
        if "COLOR" in self.jsonTblTags.keys():
            self.icolors = dict([[i, j] for j, i in self.jsonTblTags['COLOR'].items()])
        
        
        self.id = 1
        self.struct_id = 1
        
        
        
        
        #Load the hash table for the files
        json_file = open('../Data/Narikiri-Dungeon-X/Misc/hashes.json', 'r')
        self.hashes = json.load(json_file)
        json_file.close()
        
        self.repo_name          = 'Narikiri-Dungeon-X'
        self.misc               = '../Data/{}/Misc'.format(self.repo_name)
        self.disc_path          = '../Data/{}/Disc'.format(self.repo_name)
        self.story_XML_extract  = '../Data/{}/Story/'.format(self.repo_name)                       #Files are the result of PAKCOMPOSER + Comptoe here
        self.story_XML_new      = '../{}/Data/NDX/Story/XML'.format(self.repo_name)
        self.skit_extract       = '../Data/{}/Skit/'.format(self.repo_name)                                      #Files are the result of PAKCOMPOSER + Comptoe here
        
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
        self.mkdir('../Data/{}/All'.format(self.repo_name))
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
        
    # Extract each of the file from the all.dat
    def extract_files(self, start, size, filename):
        if filename in self.hashes.keys():
            filename = self.hashes[filename]
            input_file = open( self.all_original, 'rb')
            input_file.seek(start, 0)
            data = input_file.read(size)
            output_file = open( os.path.join(self.all_extract, filename), 'wb')
            output_file.write(data)
            output_file.close()
            input_file.close()
            
    
    # Extract the story files
    def extract_All_Story(self):
        
        print("Extracting Story")
        path = os.path.join( self.all_extract, 'map/pack/')
        self.mkdir(self.story_XML_extract)
        
        for f in os.listdir( path ):
            if os.path.isfile( path+f) and '.cab' in f:
                
               
                file_name = self.story_XML_extract+'New/'+f.replace(".cab", ".pak3")
                self.extract_Story_File(path+f, file_name)
                
                
                
                
        
                    #super().pakComposerAndComptoe(fileName, "-d", "-3")
        
    # Extract one single CAB file to the XML format
    def extract_Story_File(self,original_cab_file, file_name):
        
        #1) Extract CAB file to the PAK3 format
        #subprocess.run(['expand', original_cab_file, file_name])
        
        #2) Decompress PAK3 to a folder
        #self.pakcomposer("-d", file_name, os.path.join( self.story_XML_extract, "New"))
        
        if os.path.isdir(file_name.replace(".pak3", "")):
            
            #3) Grab TSS file from PAK3 folder
            tss = self.get_tss_from_pak3(  file_name.replace(".pak3", ""))
     
            #4) Extract TSS to XML
            self.extract_tss_XML(tss, original_cab_file)
        
    def get_tss_from_pak3(self, pak3_folder):
          
        
        if os.path.isdir(pak3_folder):
            folder_name = os.path.basename(pak3_folder)
          
            file_list = [os.path.dirname(pak3_folder) + "/" + folder_name + "/" + ele for ele in os.listdir(pak3_folder)]
            
            for file in file_list:
                with open(file, "rb") as f:
                    data = f.read()
                  
                    if data[0:3] == b'TSS':
                        print("... Extract TSS for file {} of size: {}".format(folder_name, len(data)))
                        return io.BytesIO(data)
    
    def extract_tss_XML(self, tss, cab_file_name):
        
        root = etree.Element('SceneText')
   
        
        tss.read(12)
        strings_offset = struct.unpack('<I', tss.read(4))[0]
        print(hex(strings_offset))
        
        tss.read(4)
        pointer_block_size = struct.unpack('<I', tss.read(4))[0]
        print(hex(pointer_block_size))
        block_size = struct.unpack('<I', tss.read(4))[0]
        #print(pointer_block_size)
        #print(block_size)
        
        
        #Create all the Nodes for Struct and grab the Person offset
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = "Story"
        texts_offset, pointers_offset = self.extract_Story_Pointers(tss, self.story_struct_byte_code, strings_offset, pointer_block_size)
        person_offset = [ self.extract_From_Struct(tss, strings_offset, pointer_offset, struct_offset, strings_node) for pointer_offset, struct_offset in zip(pointers_offset, texts_offset)]
        

        #Create all the Nodes for Strings and grab the minimum offset
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = "Other Strings"
        tss.seek(16)
        texts_offset, pointers_offset = self.extract_Story_Pointers(tss, self.story_string_byte_code, strings_offset, pointer_block_size)
        [ self.extract_From_String(tss, strings_offset, pointer_offset, text_offset, strings_node) for pointer_offset, text_offset in zip(pointers_offset, texts_offset)]
        
        text_start = min( min(person_offset), min(texts_offset))
        etree.SubElement(root, "TextStart").text = str(text_start)
  
        #Write the XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
        xml_path = os.path.join(self.story_XML_extract,"XML", self.get_file_name(cab_file_name)+".xml")
        print(xml_path)
        with open(xml_path, "wb") as xmlFile:
            xmlFile.write(txt)
    
    

    def extract_From_Struct(self, f,strings_offset, pointer_offset, struct_offset, root):
        
        
        
        #print("Offset: {}".format(hex(struct_offset)))
        f.seek(struct_offset, 0)
       
        #Unknown first pointer
        f.read(4)
        

        unknown_pointer  = struct.unpack('<I', f.read(4))[0]
        self.create_Entry(root, pointer_offset, unknown_pointer,0, "Struct")
        
        person_offset    = struct.unpack('<I', f.read(4))[0] + strings_offset
        text_offset      = struct.unpack('<I', f.read(4))[0] + strings_offset
        unknown1_offset  = struct.unpack('<I', f.read(4))[0] + strings_offset
        unknown2_offset  = struct.unpack('<I', f.read(4))[0] + strings_offset
        
        
        
        person_text      = self.bytes_to_text(f, person_offset)[0]
        self.create_Entry(root, pointer_offset, person_text,1, "Struct")
        #print("Person offset: {}".format(hex(person_offset)))
        #print("Text offset: {}".format(hex(text_offset)))
        #print("Unknown1 offset: {}".format(hex(unknown1_offset)))
        japText         = self.bytes_to_text(f, text_offset)[0]
        self.create_Entry(root, pointer_offset, japText,1, "Struct")
        
        unknown1Text     = self.bytes_to_text(f, unknown1_offset)[0]
        self.create_Entry(root, pointer_offset, unknown1Text,0, "Struct")
        #print(unknown1Text)
        unknown2Text     = self.bytes_to_text(f, unknown2_offset)[0]
        self.create_Entry(root, pointer_offset, unknown2Text,0, "Struct")
        
        
        self.struct_id += 1
        
        return person_offset
    
    def extract_From_String(self, f, strings_offset, pointer_offset, text_offset, root):
        
        
        f.seek(text_offset, 0)
        japText = self.bytes_to_text(f, text_offset)[0]
        self.create_Entry(root, pointer_offset, japText,1, "Other Strings")
    
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
    
    
 
    def create_Entry(self, strings_node, pointer_offset, text, to_translate, entry_type, speaker_id, unknown_pointer):
        
        #Add it to the XML node
        entry_node = etree.SubElement(strings_node, "Entry")
        etree.SubElement(entry_node,"PointerOffset").text = str(pointer_offset)
        etree.SubElement(entry_node,"JapaneseText").text  = str(text)  
        eng_text = ''
        
        if to_translate == 0:
            statusText = 'Done' 
            eng_text   = str(text)
            
        etree.SubElement(entry_node,"EnglishText").text   = eng_text
        etree.SubElement(entry_node,"Notes").text         = ''
        etree.SubElement(entry_node,"Id").text            = str(self.id)   
        statusText = "To Do"
        
        if entry_type == "Struct":
            etree.SubElement(entry_node,"StructId").text      = str(self.struct_id)
            etree.SubElement(entry_node,"UnknownPointer").text = str(unknown_pointer)
            
            if to_translate == 1:
                etree.SubElement(entry_node,"SpeakerId").text      = str(speaker_id)
                
        etree.SubElement(entry_node,"ToTranslate").text   = str(to_translate)             
        etree.SubElement(entry_node,"Status").text        = statusText      
        self.id += 1
        
        
        
        # Status for Unknown_Pointer, UnknownText1 and UnknownText2 should always be Done
        if (text == '') or (entry_type == "Struct" and self.id in [1,4,5])  :
            statusText = 'Done'
        else:
            statusText = 'To Do'
            
        etree.SubElement(entry_node,"Status").text        = statusText
        
        self.id += 1
    def prepare_Menu_File(self, hashes_folder):
        
        menu_file_path = "../Data/{}/Menu/New/{}".format(self.repo_name, hashes_folder)
        for filename in os.listdir(menu_file_path):
            
            if os.path.isdir(filename):
                shutil.rmtree(filename)
                
        self.unpack_Folder( menu_file_path)
        
                
    def extract_All_Menu(self):
        
        res = [self.prepare_Menu_File(ele) for ele in list(set([ele['Hashes_Name'] for ele in self.menu_files_json if ele['Hashes_Name'] != '']))]
        
        print("Extracting Menu Files")
        self.mkdir("../Data/{}/Menu/New".format(self.repo_name))
        
        for file_definition in self.menu_files_json:
           
            #if file_definition['Hashes_Name'] != '':
            #    self.prepare_Menu_File(file_definition['Hashes_Name'])
                                   
            self.extract_Menu_File(file_definition)
            
    def extract_Menu_File(self, file_definition):
        
        
        section_list = []
        pointers_offset_list = []
        texts_list = []
        to_translate = []

         
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
                    pointers_offset, pointers_value = self.get_special_pointers( text_start, text_end, base_offset, section['Pointer_Offset_Start'], section['Nb_Per_Block'], section['Step'], section['Section'], file_path)
          
              
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
                           
            #Find a possible Color, Icon
            elif b in (0x1, 0xB):
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
                        if len(hex_value) < 4 and tag_name not in ['icon','speed']:
                            hex_value = "0"*(4-len(hex_value)) + hex_value
                        
                        final_text += '<{}:{}>'.format(tag_name, hex_value)
                else:
                    final_text += "<%02X:%08X>" % (b, b2)
                 
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
                                
                                if split[0][1:] in self.itags.keys():
                                    bytesFinal += struct.pack("B", self.itags[split[0][1:]])
                                    bytesFinal += struct.pack("<I", int(split[1][:-1], 16))
                                elif split[0][1:4] == "Unk":
                                    bytesFinal += struct.pack("B", int(split[0][4:], 16))
                                    for j in [split[1][j:j+2] for j in range(0, len(split[1]) - 2, 2)]:
                                        bytesFinal += struct.pack("B", int(j, 16))
                                    bytesFinal += struct.pack("B", 0x80)
                                else:
                                    bytesFinal += struct.pack("B", int(split[0][1:], 16))
                                    bytesFinal += struct.pack("<I", int(split[1][:8], 16))
                                    
                            if c in self.jsonTblTags['NAME']:
                                bytesFinal += struct.pack("B", 0x4)
                                c = '(' + c.replace("<","").replace(">","") + ")"
                                bytesFinal += c.encode("cp932")
                                
                            if c in self.icolors:
                                bytesFinal += struct.pack("B", 0x5)
                                bytesFinal += struct.pack("<I", self.icolors[c])
                        else:
                            for c2 in c:
                                if c2 in self.itable.keys():
                                    bytesFinal += self.itable[c2]
                                else:
                                   
                                    bytesFinal += c2.encode("cp932")
           
            i=i+1
            if (nb >=2 and i<nb):
                bytesFinal += b'\x01'
        
        return bytesFinal    
        

        
        
    
    def extract_All_Skit(self):
        
        print("Extracting Skits")
        path = os.path.join( self.all_extract, 'chat/')
        skitsPath ='../Data/Archives/Skits/'
        self.mkdir(skitsPath)
        
        for f in os.listdir(path):
            if os.path.isfile(path + f):
                
                #Unpack the CAB into PAK3 file
                fileName = skitsPath + f.replace(".cab", ".pak3")
                subprocess.run(['expand', path + f, fileName])
                
                #Decompress using PAKCOMPOSER + Comptoe
                self.pakComposerAndComptoe(fileName, "-d", "-3")
    
    def extract_All_Events(self):
        
        print("Extract Events")
        path = os.path.join( self.allPathExtract, 'map/')
        eventsPath = '..Data/Archives/Events/'
        self.mkdir(eventsPath)
        
        for f in os.listdir(path):
            if os.path.isfile( path + f):
                
                #Unpack the CAB into PAK3 file
                fileName = eventsPath + f.replace(".cab", ".pak3")
                subprocess.run(['expand', path + f, fileName])
                
                #Decompress using PAKCOMPOSER + Comptoe
                self.pakComposerAndComptoe(fileName, "-d", "-3")
                
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
                self.make_Cab(name+".dat", (name+".cab").upper(), os.path.join(os.path.dirname(ele['File_Extract']), ".."))
            
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
    def extract_Main_Archive(self):
        
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
        eboot = open( os.path.join( self.misc, 'EBOOT.BIN'), 'rb')
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
                
                if len( [ele for ele in files_to_prepare if ele in final_name]) > 0:
                    copy_path = os.path.join("../Data/{}/Menu/New/{}".format(self.repo_name, final_name))
                    Path(os.path.dirname(copy_path)).mkdir(parents=True, exist_ok=True)
                    shutil.copy( os.path.join(self.all_extract, final_name), copy_path)
                
                order['order'].append(hash_)
            json.dump(order, order_json, indent = 4)
            order_json.close()
        
    def pack_Main_Archive(self):
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
                if os.path.dirname(name) in menu_files:               
                    with open( os.path.join( '../Data/{}/Menu/New'.format(self.repo_name), name), 'rb') as new_f:
                        data = new_f.read()
                else:
                    with open( os.path.join( self.all_extract, name), 'rb') as orig_f:
                        data = orig_f.read()

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
        elf.close()
        all_file.close()
        
        
        
    def extract_Decripted_Eboot(self):
        print("Extracting Eboot")
        args = ["deceboot", "../Data/{}Disc/Original/PSP_GAME/SYSDIR/EBOOT.BIN".format(self.repo_name), "../Data/{}/Misc/EBOOT_DEC.BIN".format(self.repo_name)]
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