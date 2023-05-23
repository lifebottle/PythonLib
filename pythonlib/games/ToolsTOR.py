import io
import json
import os
import re
import shutil
import struct
from dataclasses import dataclass
from itertools import tee
from pathlib import Path

import lxml.etree as etree
import pandas as pd
from tqdm import tqdm
from pythonlib.formats.scpk import Scpk

import pythonlib.utils.comptolib as comptolib
import pythonlib.formats.pak2 as pak2lib
from pythonlib.formats.theirsce import Theirsce
from pythonlib.formats.theirsce_instructions import (AluOperation, InstructionType,
                                                     TheirsceBaseInstruction)
from .ToolsTales import ToolsTales


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
    # fmt: off
    dat_bin_original    = '../Data/Tales-Of-Rebirth/Disc/Original/DAT.BIN'
    dat_bin_new         = '../Data/Tales-Of-Rebirth/Disc/New/DAT.BIN'
    elf_original        = '../Data/Tales-Of-Rebirth/Disc/Original/SLPS_254.50'
    elf_new             = '../Data/Tales-Of-Rebirth/Disc/New/SLPS_254.50'
    story_XML_new       = '../Tales-Of-Rebirth/Data/TOR/Story/'                        #Story XML files will be extracted here                      
    story_XML_patch     = '../Data/Tales-Of-Rebirth/Story/'               #Story XML files will be extracted here
    skit_XML_patch      = '../Data/Tales-Of-Rebirth/Skits/'                        #Skits XML files will be extracted here
    skit_XML_new        = '../Tales-Of-Rebirth/Data/TOR/Skits/'
    dat_archive_extract = '../Data/Tales-Of-Rebirth/DAT/' 
    # fmt: on
    
    def __init__(self, tbl):
        
        super().__init__("TOR", tbl, "Tales-Of-Rebirth")
        
        with open("../{}/Data/{}/Misc/{}".format(self.repo_name, self.gameName, self.tblFile), encoding="utf-8") as f:
            jsonRaw = json.load(f)

        for k, v in jsonRaw.items():
            self.jsonTblTags[k] = {int(k2, 16): v2 for k2, v2 in v.items()}
        
        for k, v in self.jsonTblTags.items():
            self.ijsonTblTags[k] = {v2: k2 for k2, v2 in v.items()}
        self.id = 1
        # byteCode
        self.story_byte_code = b"\xF8"
        self.string_opcode = InstructionType.STRING
        self.list_status_insertion = ['Done', 'Proofreading', 'Editing']
    
        self.mkdir('../Data/{}/DAT'.format(self.repo_name))

    # Replace n occurences of a string starting from the right
    def rreplace(self, s, old, new, occurrence):
        li = s.rsplit(old, occurrence)
        return new.join(li)

    def add_line_break(self, text):
        temp = ""
        currentLineSize = 0

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
    def extract_all_story(self, replace=False) -> None:
        print("Extracting Story files...")

        # TODO: use pathlib for everything
        folder_path = Path(self.story_XML_patch) / "XML"
        scpk_path = Path(self.dat_archive_extract) / "SCPK"

        for file in tqdm(list(scpk_path.glob("*.scpk"))):
            theirsce = Theirsce(Scpk.from_path(file).rsce)
            xml_text = self.get_xml_from_theirsce(theirsce, "Story")
            self.id = 1
            
            with open(folder_path / file.with_suffix(".xml").name, "wb") as xml:
                xml.write(xml_text)

            
    # Extract all the skits files
    def extract_all_skits(self, replace=False) -> None:
        print("Extracting Skit files...")

        # TODO: use pathlib for everything
        folder_path = Path(self.skit_XML_patch) / "XML"
        pak2_path = Path(self.dat_archive_extract) / "PAK2"

        for file in tqdm(list(pak2_path.glob("*.pak2"))):
            with open(file, "rb") as pak:
                theirsce = pak2lib.get_theirsce_from_pak2(pak.read())
            
            xml_text = self.get_xml_from_theirsce(Theirsce(theirsce), "Skits")
            
            xml_name = file.name.split(".")[0] + ".xml"
            with open(folder_path / xml_name, "wb") as xml:
                xml.write(xml_text)


    # Extract THEIRSCE to XML
    def get_xml_from_theirsce(self, rsce: Theirsce, section: str) -> bytes:
     
        #Create the XML file
        # root = etree.Element('SceneText')
        # etree.SubElement(root, "OriginalName").text = file_name

        #pointers_offset, texts_offset = self.extract_Story_Pointers(rsce)
        names, lines = self.extract_lines_with_speaker(rsce)

        for i, (k, v) in enumerate(names.items(), -1):
            names[k] = NameEntry(i, v)
  
        #Remove duplicates
        #list_informations = self.remove_duplicates(["Story"] * len(pointers_offset), pointers_offset, text_list)
        
        # list_lines = ( ['Story', line.offset, line.text] for line in lines)
        # list_names = ( ['Story', line.offset, line.text] for i, (k, v) in enumerate(found_names.items()))
        #Build the XML Structure with the information  

        root = etree.Element("SceneText")
        speakers_node = etree.SubElement(root, 'Speakers')
        etree.SubElement(speakers_node, 'Section').text = "Speaker"
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = section
        
        self.make_speakers_section(speakers_node, names)
        self.make_strings_section(strings_node, lines, names)
        
        # Return XML string
        return etree.tostring(root, encoding="UTF-8", pretty_print=True)

    
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
        finalText = ""
        tags = self.jsonTblTags['TAGS']
        chars = self.jsonTblTags['TBL']

        if (offset > 0):
            theirsce.seek(offset, 0)

        while True:
            b = theirsce.read(1)
            if b == end_strings: break

            b = ord(b)
            # Custom Encoded Text
            if (0x99 <= b <= 0x9F) or (0xE0 <= b <= 0xEB):
                c = (b << 8) | theirsce.read_uint8()
                finalText += chars.get(c, "{%02X}{%02X}" % (c >> 8, c & 0xFF))
                continue
            
            if b == 0x1:
                finalText += ("\n")
                continue
            
            # ASCII text
            if chr(b) in self.PRINTABLE_CHARS:
                finalText += chr(b)
                continue
            
            # cp932 text
            if 0xA0 < b < 0xE0:
                finalText += struct.pack("B", b).decode("cp932")
                continue

            if b == 0x81:
                next_b = theirsce.read(1)
                if next_b == b"\x40":
                    finalText += "　"
                else:
                    finalText += "{%02X}" % b
                    finalText += "{%02X}" % ord(next_b)
                continue
            
            # Simple Tags
            if 0x3 <= b <= 0xF:
                parameter = theirsce.read_uint32()

                tag_name = tags.get(b, f"{b:02X}")
                tag_param = self.jsonTblTags.get(tag_name.upper(), {}).get(parameter, None)  

                if tag_param is not None:
                    finalText += tag_param
                else:
                    finalText += f"<{tag_name}:{self.hex2(parameter)}>"

                continue
            
            # Variable tags (same as above but using rsce bytecode as parameter)
            if 0x13 <= b <= 0x1A:
                tag_name = f"unk{b:02X}"
                parameter = "".join([f"{c:02X}" for c in theirsce.read_tag_bytes()])
         
                finalText += f"<{tag_name}:{parameter}>"
                continue
            
            # None of the above
            finalText += "{%02X}" % b
       
        return finalText
    
    def get_node_bytes(self, entry_node):
        
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
            final_text = '<voice:{}>'.format(voiceId_node.text) + final_text
            
        #Convert the text values to bytes using TBL, TAGS, COLORS, ...
        bytes_entry = self.text_to_bytes(final_text)
        
        return bytes_entry
    
    
    def get_new_theirsce(self, theirsce: Theirsce, xml: Path) -> Theirsce:
        
        #To store the new text_offset and pointers to update
        new_text_offsets = dict()
              
        #Read the XML for the corresponding THEIRSCE
        
        tree = etree.parse(xml)
        root = tree.getroot()

        #Go at the start of the dialog
        #Loop on every Entry and reinsert
        theirsce.seek(theirsce.strings_offset + 1)
        nodes = [ele for ele in root.iter('Entry') if ele.find('Id').text != "-1"]
        nodes = [ele for ele in nodes if ele.find('PointerOffset').text != "-1"]

        for entry_node in nodes:

            #Add the PointerOffset and TextOffset
            new_text_offsets[entry_node.find("PointerOffset").text] = theirsce.tell()
            #Use the node to get the new bytes
            bytes_entry = self.get_node_bytes(entry_node)

            #Write to the file
            theirsce.write(bytes_entry + b'\x00')
            
        #Update the pointers based on the new text_offset of  the entries
        for pointer_offset, text_offset in new_text_offsets.items():
            
            pointers_list = pointer_offset.split(",")
            new_value = text_offset - theirsce.strings_offset

            for pointer in pointers_list:
                theirsce.seek(int(pointer))
                theirsce.write( struct.pack("<H", new_value))
            
        return theirsce
            
    #Repack SCPK files for Story
    def pack_story_file(self, scpk_file_name) -> bytes:
        
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
                if comptolib.is_compressed(data_compressed):
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
                        theirsce = self.get_new_theirsce(io.BytesIO(data_uncompressed), scpk_file_name, self.story_XML_new)
                        
                            
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
        
        with open(self.story_XML_patch + "New/" + scpk_file_name, "wb") as f:
            f.write(o.getvalue())
        
        return o.getvalue()        
    
    def pack_Skit_File(self, pak2_file):

        # Copy the original PAK2 file to the folder used for the new version
        shutil.copy(self.dat_archive_extract + "PAK2/" + pak2_file, self.skit_XML_patch + "New/" + pak2_file)

        pak2_file_path = os.path.join(self.dat_archive_extract, "PAK2", pak2_file)
        with open(pak2_file_path,"rb") as f_pak2:
            pak2_data = f_pak2.read()
        
        #Create the pak2 object
        pak2_obj = pak2lib.get_data(pak2_data)
        
        #Generate the new Theirsce based on the XML and replace the original one
        theirsce_io = self.get_new_theirsce(io.BytesIO(pak2_obj.chunks.theirsce), os.path.basename(pak2_file_path).split(".")[0], self.skit_XML_new)
        theirsce_io.seek(0)
        new_data = theirsce_io.read()
        pak2_obj.chunks.theirsce = new_data
        
        self.mkdir(self.skit_XML_patch+ "New")
        with open(self.skit_XML_patch+ "New/" + pak2_file, "wb") as f2:
            f2.write(pak2lib.create_pak2(pak2_obj))
            
        return

    def pack_all_skits(self):
        print("Recreating Skit files...")

        # TODO: use pathlib for everything
        out_path = Path(self.skit_XML_patch) / "New"
        xml_path = Path(self.skit_XML_new) / "XML"
        pak2_path = Path(self.dat_archive_extract) / "PAK2"

        for file in (pbar:= tqdm(list(pak2_path.glob("*.pak2")))):
            pbar.set_description_str(file.name)
            with open(file, "rb") as f:
                pak2_data = f.read()
            pak2_obj = pak2lib.get_data(pak2_data)

            old_rsce = Theirsce(pak2_obj.chunks.theirsce)
            xml_name = file.name.split(".")[0] + ".xml"
            new_rsce = self.get_new_theirsce(old_rsce, xml_path / xml_name)
            new_rsce.seek(0)
            pak2_obj.chunks.theirsce = new_rsce.read()
            
            with open(out_path / file.name, "wb") as f:
                f.write(pak2lib.create_pak2(pak2_obj))

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

            
    def get_datbin_file_data(self) -> list[tuple[int, int]]:

        with open(self.elf_original , "rb") as elf:
            elf.seek(self.POINTERS_BEGIN, 0)
            blob = elf.read(self.POINTERS_END-self.POINTERS_BEGIN)
            
        pointers = struct.unpack(f"<{len(blob)//4}L", blob)
        file_data: list[tuple[int, int]] = []
        for c, n in zip(pointers, pointers[1:]):
            remainder = c & self.LOW_BITS
            start = c & self.HIGH_BITS
            end = (n & self.HIGH_BITS) - remainder
            file_data.append((start, end - start)) 
        
        return file_data

    # Extract the file DAT.BIN to the different directorties
    def extract_main_archive(self) -> None:
        
        print("Cleaning extract folder...")
        for path in Path(self.dat_archive_extract).glob("**/*"):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)

        print("Extracting DAT.BIN files...")
        with open( self.dat_bin_original, "rb") as f:
            for i, (offset, size) in enumerate(tqdm(self.get_datbin_file_data(), desc="Extracting files", unit="file")):
                
                # Ignore 0 byte files
                if size == 0:
                    continue

                f.seek(offset, 0)
                data = f.read(size)
                
                if comptolib.is_compressed(data):
                    c_type = struct.unpack("<b", data[:1])[0]
                    data = comptolib.decompress_data(data)
                    extension = self.get_extension(data)
                    fname = f"{i:05d}.{c_type}.{extension}"
                else:
                    extension = self.get_extension(data)
                    fname = f"{i:05d}.{extension}"
                
                # TODO: use pathlib for everything
                final_path = Path(self.dat_archive_extract) / extension.upper()
                final_path.mkdir(parents=True, exist_ok=True)
        
                with open(final_path / fname, "wb") as output:
                    output.write(data)
        
        
    def pack_main_archive(self):
        sectors = [0]
        remainders = []
        buffer = 0

        # Copy the original SLPS to Disc/New
        shutil.copy(self.elf_original, self.elf_new)
   
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
        
    
            for file in tqdm(sorted(file_list, key=self.get_file_name)):
             
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
        
        #Use the new SLPS updated and update the pointers for the SCPK
        with open("../Data/{}/Disc/New/SLPS_254.50".format(self.repo_name), "r+b") as output_elf:
            output_elf.seek(self.POINTERS_BEGIN)
        
            for i in range(len(sectors) - 1):
                output_elf.write(struct.pack("<L", sectors[i] + remainders[i]))
    
        
    def pack_all_story(self):
        print("Recreating Story files...")

        # TODO: use pathlib for everything
        out_path = Path(self.story_XML_patch) / "New"
        xml_path = Path(self.story_XML_new) / "XML"
        scpk_path = Path(self.dat_archive_extract) / "SCPK"

        for file in (pbar:= tqdm(list(scpk_path.glob("*.scpk")))):
            pbar.set_description_str(file.name)
            curr_scpk = Scpk.from_path(file)
            old_rsce = Theirsce(curr_scpk.rsce)
            new_rsce = self.get_new_theirsce(old_rsce, xml_path / file.with_suffix(".xml").name)
            new_rsce.seek(0)
            curr_scpk.rsce = new_rsce.read()
            
            with open(out_path / file.name, "wb") as f:
                f.write(curr_scpk.to_bytes())

            
    def insert_All(self):
        
        #Updates SCPK based on XMLs data
        
        self.pack_main_archive()