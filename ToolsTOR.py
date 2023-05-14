from dataclasses import dataclass
from itertools import tee
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
import pak2 as pak2lib
from theirsce import Theirsce
from theirsce_instructions import AluOperation, InstructionType, ReferenceScope, TheirsceBaseInstruction, TheirsceReferenceInstruction, TheirsceStringInstruction

@dataclass
class LineEntry:
    names: list[str]
    text: str
    offset: int

@dataclass
class NameEntry:
    index: int
    offsets: list[int]


VARIABLE_NAME = "[VARIABLE]"

class ToolsTOR(ToolsTales):
    
    POINTERS_BEGIN = 0xD76B0                                            # Offset to DAT.BIN pointer list start in SLPS_254.50 file
    POINTERS_END   = 0xE60C8                                            # Offset to DAT.BIN pointer list end in SLPS_254.50 file
    HIGH_BITS      = 0xFFFFFFC0
    LOW_BITS       = 0x3F
    
    
    #Path to used
    dat_bin_original   = '../Data/Tales-Of-Rebirth/Disc/Original/DAT.BIN'
    dat_bin_new        = '../Data/Tales-Of-Rebirth/Disc/New/DAT.BIN'
    elf_original      = '../Data/Tales-Of-Rebirth/Disc/Original/SLPS_254.50'
    elf_new           = '../Data/Tales-Of-Rebirth/Disc/New/SLPS_254.50'
    story_XML_new    = '../Tales-Of-Rebirth/Data/TOR/Story/'                        #Story XML files will be extracted here                      
    story_XML_patch  = '../Data/Tales-Of-Rebirth/Story/'               #Story XML files will be extracted here
    skit_XML_patch   = '../Data/Tales-Of-Rebirth/Skits/'                        #Skits XML files will be extracted here
    skit_XML_new = '../Tales-Of-Rebirth/Data/TOR/Skits/'
    dat_archive_extract   = '../Data/Tales-Of-Rebirth/DAT/' 
    
    def __init__(self, tbl):
        
        super().__init__("TOR", tbl, "Tales-Of-Rebirth")
        
        with open("../{}/Data/{}/Misc/{}".format(self.repo_name, self.gameName, self.tblFile), encoding="utf-8") as f:
                       
            jsonRaw = json.load(f)       
            self.jsonTblTags ={ k1:{ int(k2,16) if (k1 != "TBL") else k2:v2 for k2,v2 in jsonRaw[k1].items()} for k1,v1 in jsonRaw.items()}
            
          
            
        self.itable = dict([[i, struct.pack(">H", int(j))] for j, i in self.jsonTblTags['TBL'].items()])
        self.itags = dict([[i, j] for j, i in self.jsonTblTags['TAGS'].items()])
        if "NAME" in self.jsonTblTags.keys():
            self.inames = dict([[i, j] for j, i in self.jsonTblTags['NAME'].items()])
        
        if "COLOR" in self.jsonTblTags.keys():
            self.icolors = dict([[i, j] for j, i in self.jsonTblTags['COLOR'].items()])
        self.id = 1
        
        #byteCode 
        self.story_byte_code = b"\xF8"
        self.string_opcode = InstructionType.STRING
        self.list_status_insertion = ['Done', 'Proofreading']
    
        self.mkdir('../Data/{}/DAT'.format(self.repo_name))

    # Replace n occurences of a string starting from the right
    def rreplace(self, s, old, new, occurrence):
        li = s.rsplit(old, occurrence)
        return new.join(li)

    def add_line_break(self, text):
        temp = "";
        currentLineSize = 0;

        text_size = len(text)
        max_size = 32
        split_space = text.split(" ")

        for word in split_space:
            currentLineSize += (len(word) + 1)

            if currentLineSize <= max_size:
                temp = temp + word + ' '

            else:
                temp = temp + '\n' + word + ' '
                currentLineSize = 0

        temp = temp.replace(" \n", "\n")
        temp = self.rreplace(temp, " ", "", 1)

        return temp
    def clean_text(self, text):
        text = re.sub(r"\n ", "\n", text)
        text = re.sub(r"\n", "", text)
        text = re.sub(r"(<\w+:?\w+>)", "", text)
        text = re.sub(r"\[\w+=*\w+\]", "", text)
        text = re.sub(r" ", "", text)
        text = re.sub(u'\u3000', '', text)
        text = re.sub(r" ", "", text)
        return text

    # Extract/Transform Lauren translation
    def extract_Lauren_Translation(self):

        # Load Lauren's googlesheet data inside a dataframe
        df = self.extract_Google_Sheets("1-XwzS7F0SaLlXwv1KS6RcTEYYORH2DDb1bMRy5VM5oo", "Story")

        # 1) Make some renaming and transformations
        df = df.rename(columns={"KEY": "File", "Japanese": "JapaneseText", "Lauren's Script": "EnglishText"})

        # 2) Filter only relevant rows and columns from the googlesheet
        df = df.loc[(df['EnglishText'] != "") & (df['JapaneseText'] != ""), :]
        df = df[['File', 'JapaneseText', 'EnglishText']]

        # 3) Make some transformations to the JapaneseText so we can better match with XML
        df['File'] = df['File'].apply(lambda x: x.split("_")[0] + ".xml")
        df['JapaneseText'] = df['JapaneseText'].apply(lambda x: self.clean_text(x))
        return df

    # Transfer Lauren translation
    def transfer_Lauren_Translation(self):

        df_lauren = self.extract_Lauren_Translation()

        # Distinct list of XMLs file
        xml_files = list(set(df_lauren['File'].tolist()))

        for file in xml_files:
            cond = df_lauren['File'] == file
            lauren_translations = dict(df_lauren[cond][['JapaneseText', 'EnglishText']].values)
            file_path = self.story_XML_new + 'XML/' + file

            if os.path.exists(file_path):
                tree = etree.parse(file_path)
                root = tree.getroot()
                need_save = False

                for key, item in lauren_translations.items():

                    for entry_node in root.iter("Entry"):
                        xml_jap = entry_node.find("JapaneseText").text or ''
                        xml_eng = entry_node.find("EnglishText").text or ''
                        xml_jap_cleaned = self.clean_text(xml_jap)

                        if key == xml_jap_cleaned:
                            item = self.add_line_break(item)

                            if xml_eng != item:
                                entry_node.find("EnglishText").text = item
                                need_save = True

                                if entry_node.find("Status").text == "To Do":
                                    entry_node.find("Status").text = "Editing"

                        # else:
                        #    print("File: {} - {}".format(file, key))

                if need_save:
                    txt = etree.tostring(root, encoding="UTF-8", pretty_print=True, xml_declaration=False)

                    with open(file_path, 'wb') as xml_file:
                        xml_file.write(txt)

            else:
                print("File {} skipped because file is not found".format(file))

    # Extract the story files
    def extract_All_Story(self,replace=False):

        print("Extracting Story files")
        print(replace)
        i = 1
        self.mkdir( self.story_XML_patch + "XML")
        listFiles = [self.dat_archive_extract + 'SCPK/' + ele for ele in os.listdir( os.path.join(self.dat_archive_extract, "SCPK"))]
        for scpk_file in listFiles:
            
            theirsce = self.get_theirsce_from_scpk(scpk_file)
            self.extract_TheirSce_XML(theirsce, scpk_file, self.story_XML_patch, "Story", replace)
            self.id = 1
            print("Writing file %05d.." % i, end="\r") # Not healthy
            i += 1
        print("Writing file %05d..." % (i-1))
            
    # Extract all the skits files
    def extract_All_Skits(self, replace=False):
        i = 1
        os.makedirs( self.skit_XML_patch + "XML", exist_ok=True)
        list_pak2_files = [ self.dat_archive_extract + "PAK2/" + ele for ele in os.listdir(self.dat_archive_extract + "PAK2")]
        for file_path in list_pak2_files:
           
            if os.path.isfile(file_path) and file_path.endswith(".pak2"):
                with open(file_path, "rb") as pak:
                    data = pak.read()
                theirsce = io.BytesIO(pak2lib.get_theirsce_from_pak2(data))
                self.extract_TheirSce_XML(theirsce, re.sub("\.\d+", "", file_path), self.skit_XML_patch, "Skits", replace)
                
                print("Writing file %05d" % i, end="\r")
                i += 1
    
        print("Writing file %05d..." % (i-1))
        return
        
    def get_theirsce_from_scpk(self, scpk_file_name, debug=False)->bytes:
        
        with open(scpk_file_name,"rb") as scpk:
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
    
                if self.is_compressed(data) and data[:8] != b"THEIRSCE":
                    data_decompressed = comptolib.decompress_data(data)
                    
                if data_decompressed[:8] == b"THEIRSCE":
                
                    return io.BytesIO(data_decompressed)
    
            return None
    
   
        
    
        
    # Extract THEIRSCE to XML
    def extract_TheirSce_XML(self, theirsce, file_name, destination, section, replace):
     
        #Create the XML file
        # root = etree.Element('SceneText')
        # etree.SubElement(root, "OriginalName").text = file_name

        rsce = Theirsce(path=theirsce)
        #pointers_offset, texts_offset = self.extract_Story_Pointers(rsce)
        names, lines = self.extract_lines_with_speaker(rsce)

        for i, (k, v) in enumerate(names.items(), -1):
            names[k] = NameEntry(i, v)
  
        #Remove duplicates
        #list_informations = self.remove_duplicates(["Story"] * len(pointers_offset), pointers_offset, text_list)
        
        # list_lines = ( ['Story', line.offset, line.text] for line in lines)
        # list_names = ( ['Story', line.offset, line.text] for i, (k, v) in enumerate(found_names.items()))
        #Build the XML Structure with the information  
        
        file_path = destination +"XML/"+ self.get_file_name(file_name)

        root = etree.Element("SceneText")
        speakers_node = etree.SubElement(root, 'Speakers')
        etree.SubElement(speakers_node, 'Section').text = "Speaker"
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = section
        
        self.make_speakers_section(speakers_node, names)
        self.make_strings_section(strings_node, lines, names)
        
        #Write the XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
    
        with open(os.path.join( destination,"XML", self.get_file_name(file_name)+".xml"), "wb") as xmlFile:
            xmlFile.write(txt)

        if replace:
            self.copy_XML_Translations(
                '../{}/Data/{}/{}/XML/{}.xml'.format(self.repo_name, self.gameName, section, self.get_file_name(file_name)),
                '../Data/{}/{}/XML/{}.xml'.format(self.repo_name,  section, self.get_file_name(file_name))
            )
    
    def make_strings_section(self, root, lines: list[LineEntry], names: dict[str, NameEntry]):
        pass
        for line in lines:
            entry_node = etree.SubElement(root, "Entry")
            etree.SubElement(entry_node,"PointerOffset").text = str(line.offset)
            text_split = list(filter(None, re.split(self.COMMON_TAG, line.text)))
            
            if len(text_split) > 1 and text_split[0].startswith("<voice:"):
                etree.SubElement(entry_node,"VoiceId").text  = text_split[0][1:-1].split(":")[1]
                etree.SubElement(entry_node, "JapaneseText").text = ''.join(text_split[1:])
            else:
                etree.SubElement(entry_node, "JapaneseText").text = line.text
            
            etree.SubElement(entry_node,"EnglishText")
            etree.SubElement(entry_node,"Notes")

            if line.names:
                etree.SubElement(entry_node,"SpeakerId").text = ','.join([str(names[n].index) for n in line.names])
            etree.SubElement(entry_node,"Id").text = str(self.id)
            
            self.id = self.id + 1
            
            if line.text == '':
                statusText = 'Done'
            else:
                statusText = 'To Do'
            etree.SubElement(entry_node,"Status").text        = statusText
        
    
    def make_speakers_section(self, root, names: dict[str, NameEntry]):
        for k, v in names.items():
            entry_node = etree.SubElement(root, "Entry")
            if v.offsets:
                etree.SubElement(entry_node,"PointerOffset").text = ",".join([str(off) for off in v.offsets])
            else:
                etree.SubElement(entry_node,"PointerOffset")
            etree.SubElement(entry_node,"JapaneseText").text  = str(k)
            etree.SubElement(entry_node,"EnglishText")
            etree.SubElement(entry_node,"Notes")
            etree.SubElement(entry_node,"Id").text            = str(v.index)
            etree.SubElement(entry_node,"Status").text         = "To Do"

    
    def extract_lines_with_speaker(self, theirsce: Theirsce):
        # This will do a bit of everything thanks to the "nice"
        # architecture of the Theirsce class :)
    
        # Debug
        # sections = []
        # for _, section in enumerate(theirsce.sections):
        #     for _, sub in enumerate(section):
        #         sections.append(sub.off)

        # Setup three-way opcode generator
        d = TheirsceBaseInstruction(); d.type = InstructionType.INVALID
        a,b,c = tee(theirsce.walk_code(), 3)
        next(a, d)
        next(b, d); next(b, d)
        next(c, d); next(c, d); next(c, d)

        # Helper function, in the future I'll
        # just use a list of opcodes
        def skip():
            next(a, d); next(a, d)
            next(b, d); next(b, d)
            next(c, d); next(c, d)
        
        
        names = {VARIABLE_NAME: []}
        lines = []
        params = []
        used = False
        for op1, op2, op3 in zip(a,b,c):
            # Debug
            # if theirsce.tell() in sections:
            #     print()
            #     print("SECTION: ")

            # BREAK marks start of a local function
            # so local params are no longer in scope
            if op1.type is InstructionType.BREAK:
                if used == False:
                    for param in params:
                        text = self.bytes_to_text(theirsce, param.offset + theirsce.strings_offset)
                        lines.append(LineEntry([], text, op1.position + 1))
                params.clear()

                continue

            # This sequence mark the simple act of assigning
            # a string to a local variable, so we can detect
            # when they are used later in a function call
            if (op1.type is InstructionType.REFERENCE
                and op2.type is InstructionType.STRING 
                and op3.type is InstructionType.ALU
                and op3.operation == AluOperation.ASSIGNMENT 
                ):
                params.append(op2)
                skip()
                continue

            # This sequence represents the textbox call with
            # the name being a variable (NPCs do this)
            if (op1.type is InstructionType.REFERENCE
                and op2.type is InstructionType.STRING 
                and op3.type is InstructionType.SYSCALL
                and op3.function_index == 0x45
                ):
                if len(params) >= 1:
                    name = [self.bytes_to_text(theirsce, p.offset + theirsce.strings_offset) for p in params]
                    [names.setdefault(n, []).append(p.position + 1) for n, p in zip(name, params)]
                elif len(params) == 0:
                    name = []
                text = self.bytes_to_text(theirsce, op2.offset + theirsce.strings_offset)
                lines.append(LineEntry(name, text, op2.position + 1))
                #print(f"{params}: {text}")
                used = True
                skip()
                continue
            
            # This sequence represents the textbox call with
            # the text being a variable (Notice boxes do this)
            if (op1.type is InstructionType.STRING
                and op2.type is InstructionType.REFERENCE 
                and op3.type is InstructionType.SYSCALL
                and op3.function_index == 0x45
                ):
                name = [self.bytes_to_text(theirsce, op1.offset + theirsce.strings_offset)]
                names.setdefault(name[0], []).append(op1.position + 1)
                for param in params:
                    text = self.bytes_to_text(theirsce, param.offset + theirsce.strings_offset)
                    lines.append(LineEntry(name, text, param.position + 1))
                    #print(f"{text}: {name}")
                used = True
                params.clear()
                skip()
                continue
            
            # This sequence represents a regular textbox call
            # where both fields are an string (everything else, save for skits)
            if (op1.type is InstructionType.STRING
                and op2.type is InstructionType.STRING
                and op3.type is InstructionType.SYSCALL
                and op3.function_index == 0x45
                ):
                name = [self.bytes_to_text(theirsce, op1.offset + theirsce.strings_offset)]
                names.setdefault(name[0], []).append(op1.position + 1)
                text = self.bytes_to_text(theirsce, op2.offset + theirsce.strings_offset)
                lines.append(LineEntry(name, text, op2.position + 1))
                #print(f"{name}: {text}")
                skip()
                continue
            
            # Any other string in assorted code calls
            if op1.type is InstructionType.STRING:
                #print(theirsce.read_string_at(op1.offset + theirsce.strings_offset))
                text = self.bytes_to_text(theirsce, op1.offset + theirsce.strings_offset)
                lines.append(LineEntry([], text, op1.position + 1))
                continue
        
        return names, lines


    def extract_story_pointers_plain(self, theirsce: Theirsce):
        pointers_offset = []; texts_offset = []

        for opcode in theirsce.walk_code():
            if opcode.type == self.string_opcode:
                pointers_offset.append(theirsce.tell() - 2) # Maybe check this later
                texts_offset.append(opcode.offset + theirsce.strings_offset)
                    
        return pointers_offset, texts_offset

    #Convert a bytes object to text using TAGS and TBL in the json file
    def bytes_to_text(self, theirsce: Theirsce, offset=-1, end_strings = b"\x00"):
    
        finalText = ''
        TAGS = self.jsonTblTags['TAGS']
        
        if (offset > 0):
            theirsce.seek(offset, 0)
        
        pos = theirsce.tell()
        b = theirsce.read(1)
        while b != end_strings:
            #print(hex(fileRead.tell()))
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
                    tag_search = tag_name.upper()
                    if (tag_search in self.jsonTblTags.keys()):
                        tags2 = self.jsonTblTags[tag_search]
                        tag_param = tags2.get(b2, None) 
                    if tag_param != None:
                        finalText += tag_param
                    else:
                        #Pad the tag to be even number of characters
                        hex_value = self.hex2(b2)
                        if len(hex_value) < 4 and tag_name not in ['icon','speed']:
                            hex_value = "0"*(4-len(hex_value)) + hex_value
                        
                        finalText += '<{}:{}>'.format(tag_name, hex_value)
                        #finalText += ("<%s:%08X>" % (tag_name, b2))
                else:
                    finalText += "<%02X:%08X>" % (b, b2)
            elif chr(b) in self.PRINTABLE_CHARS:
                finalText += chr(b)
            elif b >= 0xA1 and b < 0xE0:
                finalText += struct.pack("B", b).decode("cp932")
            elif b in (0x13, 0x17, 0x1A):
                tag_name = f"Unk{b:02X}"
                hex_value = ""
                
                while theirsce.read(1) != b"\x80":
                    theirsce.seek(theirsce.tell()-1)
                    mark = theirsce.read(1)
                    hex_value += mark.hex()
                    if mark == "\x38":
                        hex_value += f"{struct.unpack('<H', theirsce.read(2))[0]:04X}"
         
                finalText += '<{}:{}>'.format(tag_name, hex_value)
                
            elif b in (0x18, 0x19):
                tag_name = f"Unk{b:02X}"
                hex_value = ""
 
                while theirsce.read(1) != b"\x80":
                    theirsce.seek(theirsce.tell()-1)
                    hex_value += theirsce.read(1).hex()
         
                finalText += '<{}:{}>'.format(tag_name, hex_value)

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
       
        end = theirsce.tell()
        size = theirsce.tell() - pos - 1
        theirsce.seek(pos)
        hex_string = theirsce.read(size).hex()
        hex_values = ' '.join(a+b for a,b in zip(hex_string[::2], hex_string[1::2]))
        theirsce.seek(end)
        #return finalText, hex_values
        return finalText
    
    def get_Node_Bytes(self, entry_node):
        
        #Grab the fields from the Entry in the XML
        status = entry_node.find("Status").text
        japanese_text = entry_node.find("JapaneseText").text
        english_text = entry_node.find("EnglishText").text
        
        #Use the values only for Status = Done and use English if non empty
        final_text = ''
        if (status in self.list_status_insertion):
            final_text = english_text or japanese_text or ''
        else:
            final_text = japanese_text or ''
        
        voiceId_node = entry_node.find("VoiceId")
        if (voiceId_node != None):
            final_text = voiceId_node.text + final_text 
            
        #Convert the text values to bytes using TBL, TAGS, COLORS, ...
        bytes_entry = self.text_to_bytes(final_text)
        
        return bytes_entry   
    
    def get_New_Theirsce(self, theirsce, scpk_file_name, destination):
        
        #To store the new text_offset and pointers to update
        new_text_offsets = dict()
        
        #Grab strings_offset for pointers
        theirsce.read(12)
        strings_offset = struct.unpack("<L", theirsce.read(4))[0]
              
        #Read the XML for the corresponding THEIRSCE
        file = destination +"XML/"+ self.get_file_name(scpk_file_name)+'.xml'
        #print("XML : {}".format(self.get_file_name(scpk_file_name)+'.xml'))
        
        tree = etree.parse(file)
        root = tree.getroot()

        #Go at the start of the dialog
        #Loop on every Entry and reinsert
        theirsce.seek(strings_offset+1)
        nodes = [ele for ele in root.iter('Entry') if ele.find('Id').text != "-1"]
        nodes = [ele for ele in nodes if ele.find('PointerOffset').text != '-1']
        print(file)
        for entry_node in nodes:

            #Add the PointerOffset and TextOffset
            new_text_offsets[entry_node.find("PointerOffset").text] = theirsce.tell()
            print(entry_node.find("PointerOffset").text)
            #Use the node to get the new bytes
            bytes_entry = self.get_Node_Bytes(entry_node)

            #Write to the file
            theirsce.write(bytes_entry + b'\x00')
            
        #Update the pointers based on the new text_offset of  the entries
        for pointer_offset, text_offset in new_text_offsets.items():
            
            pointers_list = pointer_offset.split(",")
            new_value = text_offset - strings_offset


            for pointer in pointers_list:
                
                theirsce.seek(int(pointer))
                theirsce.write( struct.pack("<H", new_value))
            
        return theirsce
            
    #Repack SCPK files for Story
    def pack_Story_File(self, scpk_file_name):
        
        #Copy the original SCPK file to the folder used for the new version
        shutil.copy( self.dat_archive_extract + "SCPK/" + scpk_file_name, self.story_XML_patch + "New/" + scpk_file_name)
        
        #Open the original SCPK
        with open( self.dat_archive_extract + "SCPK/" + scpk_file_name, 'r+b') as scpk:
              
            
            #Get nb_files and files_size
            scpk.read(4)
            scpk.read(4)
            nb_files = struct.unpack("<L", scpk.read(4))[0]
            scpk.read(4)
            file_size_dict = dict()
            for i in range(nb_files):
                pointer_offset = scpk.tell()
                file_size = struct.unpack("<L", scpk.read(4))[0]
                file_size_dict[pointer_offset] = file_size
                         
            #Extract each files and append to the final data_final
            dataFinal = bytearray()
            sizes = []
            o = io.BytesIO()

            i=0
            for pointer_offset, fsize in file_size_dict.items():
                
                data_compressed = scpk.read(fsize)
       
                    
                
                
                if self.is_compressed(data_compressed):
                    c_type = struct.unpack("<b", data_compressed[:1])[0]
                    #print("File {}   size: {}    ctype: {}".format(i, fsize,c_type))
                    data_uncompressed = comptolib.decompress_data(data_compressed)

                    if data_uncompressed[:8] == b"THEIRSCE":
                        
                        #Only for debug to have  the original THEIRSCE
                        #with open("test_original_comp.theirsce", "wb") as f:
                        #    print("Size original: {}".format(len(data_uncompressed)))
                        #    f.write(data)
                        #with open("test_original.theirsce", "wb") as f:
                        #    f.write(data_uncompressed)
                            
                        #Update THEIRSCE uncompressed file
                        theirsce = self.get_New_Theirsce(io.BytesIO(data_uncompressed), scpk_file_name, self.story_XML_new)
                        
                            
                        theirsce.seek(0)
                        data_new_uncompressed = theirsce.read()
                        data_compressed = comptolib.compress_data(data_new_uncompressed, version=c_type)
                        
                    else:
                        data_compressed = comptolib.compress_data(data_uncompressed, version=c_type)

                    
                            
                #Updating the header of the SCPK file to adjust the size
                new_size = len(data_compressed)  
                #print("File recomp {}   size: {}    ctype: {}".format(i, new_size,c_type))
                            
                dataFinal += data_compressed
                sizes.append(new_size)
                i=i+1
                
        
        #Write down the new SCPK from scratch
        o.write(b"\x53\x43\x50\x4B\x01\x00\x0F\x00")
        o.write(struct.pack("<L", len(sizes)))
        o.write(b"\x00" * 4)
    
        for i in range(len(sizes)):
            o.write(struct.pack("<L", sizes[i]))
        
        o.write(dataFinal)
        
        #with open("10247.scpk", "wb") as f:
        #    f.write(o.getvalue())
        
        return o.getvalue()        
    
    def pack_Skit_File(self, pak2_file):
        
        pak2_file_path = os.path.join(self.dat_archive_extract, "PAK2", pak2_file)
        with open(pak2_file_path,"rb") as f_pak2:
            pak2_data = f_pak2.read()
        
        #Create the pak2 object
        pak2_obj = pak2lib.pak2_file()
        pak2_obj = pak2lib.get_data(pak2_data)
        
        #Generate the new Theirsce based on the XML and replace the original one
        theirsce_io = self.get_New_Theirsce(io.BytesIO(pak2_obj.chunks.theirsce), os.path.basename(pak2_file_path).split(".")[0], self.skit_XML_new)
        theirsce_io.seek(0)
        new_data = theirsce_io.read()
        pak2_obj.chunks.theirsce = new_data
        
        self.mkdir(self.skit_XML_patch+ "New")
        #with open(self.skit_XML_patch+ "New/" + pak2_file, "wb+") as f2:
        #    f2.write(pak2lib.create_pak2(pak2_obj))
            
        return pak2lib.create_pak2(pak2_obj)

    def pack_All_Skits(self):

        print("Recreating Skits files")
        listFiles = [ele for ele in os.listdir(self.skit_XML_patch + "New/")]
        for pak2_file in listFiles:
            self.pack_Skit_File(pak2_file)
            print("Writing file {} ...".format(pak2_file))

    def debug_Story_Skits(self, section, file_name, text=False):

        if section == "Story":
            theirsce = self.get_theirsce_from_scpk(self.dat_archive_extract + 'SCPK/' + self.get_file_name(file_name) + '.scpk')
        else:
            with open(self.dat_archive_extract + "PAK2/" + file_name.split(".")[0] + '.3.pak2', "rb") as pak:
                data = pak.read()
            theirsce = io.BytesIO(pak2lib.get_theirsce_from_pak2(data))

        rsce = Theirsce(path=theirsce)
        # pointers_offset, texts_offset = self.extract_Story_Pointers(rsce)
        names, lines = self.extract_lines_with_speaker(rsce)

        for i, (k, v) in enumerate(names.items(), -1):
            names[k] = NameEntry(i, v)

        with open('../{}.theirsce'.format(file_name), 'wb') as f:
            f.write(theirsce.getvalue())

        text_list = []
        if text:
            text_list = [line.text for line in lines]

        df = pd.DataFrame({"Jap_Text": text_list})
        df['Text_Offset'] = df['Text_Offset'].apply(lambda x: hex(x)[2:])
        df['Pointers_Offset'] = df['Pointers_Offset'].apply(lambda x: hex(x)[2:])
        df.to_excel('../{}.xlsx'.format(self.get_file_name(file_name)), index=False)

    # Extract the file DAT.BIn to the different directorties
    def extract_Main_Archive(self):
        
        print("Extracting DAT bin files")
        self.mkdir("../Data/Tales-Of-Rebirth/DAT")
               
        
        f = open( self.dat_bin_original, "rb")
    
        pointers = self.get_pointers(self.POINTERS_BEGIN)
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
            
            
            compto_flag = True
            if self.is_compressed(data) and compto_flag:
                c_type = struct.unpack("<b", data[:1])[0]
                data = comptolib.decompress_data(data)
                extension = self.get_extension(data)
                final_path = self.dat_archive_extract + "/%s/%s.%d.%s" % (
                    extension.upper(),
                    file_name,
                    c_type,
                    extension,
                )
            else:
                extension = self.get_extension(data)
                final_path = self.dat_archive_extract + "/%s/%s.%s" % (
                    extension.upper(),
                    file_name,
                    extension,
                )
            folderPath = os.path.join( self.dat_archive_extract, extension.upper())
            self.mkdir( folderPath )
    
            with open(final_path, "wb") as output:
                output.write(data)
            print("Writing file %05d/%05d..." % (i, total_files), end="\r")
    
        print("Writing file %05d/%05d..." % (i, total_files))
        f.close()
        
        
    def pack_Main_Archive(self):
        sectors = [0]
        remainders = []
        buffer = 0
    
    
   
        output_dat_path = self.dat_bin_new
        with open(output_dat_path, "wb") as output_dat:
    
            print("Packing files into %s..." % os.path.basename(output_dat_path))
            
            #Make a list with all the files of DAT.bin
            file_list = []
            for path, subdir, filenames in os.walk(self.dat_archive_extract):
                if len(filenames) > 0:
                    file_list.extend( [os.path.join(path,file) for file in filenames])
                
                
            list_test = [os.path.splitext(os.path.basename(ele))[0] for ele in file_list]
            previous = -1
            dummies = 0
        
    
            for file in sorted(file_list, key=self.get_file_name):
             
                size = 0
                remainder = 0
                current = int(re.search(self.VALID_FILE_NAME, file).group(1))
                
                if current != previous + 1:
                    while previous < current - 1:
                        remainders.append(remainder)
                        buffer += size + remainder
                        sectors.append(buffer)
                        previous += 1
                        dummies += 1
                file_name = self.get_file_name(file)
                
                if ".scpk" in file:
                    path = os.path.join(self.story_XML_patch, 'New', '{}.scpk'.format(file_name))
                    print(path)

                elif ".pak2" in file:
                    path = os.path.join(self.skit_XML_patch, 'New', '{}.pak2'.format(file_name))
                    print(path)
                else:
                    path = file

                with open(path, "rb") as f2:
                    data = f2.read()
                #data = f2.read()  
                
                comp_type = re.search(self.VALID_FILE_NAME, file).group(2)
                if comp_type != None:
                    data = comptolib.compress_data(data, version=int(comp_type))
            
                output_dat.write(data)
                size = len(data)
                #print("file: {}   size: {}".format(file, size))
                remainder = 0x40 - (size % 0x40)
                if remainder == 0x40:
                    remainder = 0
                output_dat.write(b"\x00" * remainder)
              
        
                remainders.append(remainder)
                buffer += size + remainder
                sectors.append(buffer)
                previous += 1
        
                #print(
                #    "Writing file %05d/%05d..." % (current - dummies, len(file_list)), end="\r"
                #)
        
            print("Writing file %05d/%05d..." % (current - dummies, len(file_list)))
        
        #Use the new SLPS updated and update the pointers for the SCPK
        with open("../Data/{}/Disc/New/SLPS_254.50".format(self.repo_name), "r+b") as output_elf:
            output_elf.seek(self.POINTERS_BEGIN)
        
            for i in range(len(sectors) - 1):
                output_elf.write(struct.pack("<L", sectors[i] + remainders[i]))
    
        
    def pack_All_Story(self):
        
        print("Recreating Story files")
        listFiles = [ele for ele in os.listdir( self.story_XML_patch + "New/")]
        for scpk_file in listFiles:
            self.pack_Story_File(scpk_file)
            print("Writing file {} ...".format(scpk_file))
            
    def insert_All(self):
        
        #Updates SCPK based on XMLs data
        
        self.pack_Main_Archive()