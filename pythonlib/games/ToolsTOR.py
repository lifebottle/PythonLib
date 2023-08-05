import io
import pyjson5 as json
import re
import shutil
import struct
from dataclasses import dataclass
from itertools import tee
from pathlib import Path

import lxml.etree as etree
import pandas as pd
import pycdlib
from tqdm import tqdm
from pythonlib.formats.FileIO import FileIO
from pythonlib.formats.pak import Pak
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

    
    def __init__(self, project_file: Path) -> None:
        base_path = project_file.parent
        self.jsonTblTags = {}
        self.ijsonTblTags = {}
        with open(project_file, encoding="utf-8") as f:
            jsonRaw = json.load(f)

        self.paths: dict[str, Path] = {k: base_path / v for k, v in jsonRaw["paths"].items()}
        self.main_exe_name = jsonRaw["main_exe_name"]

        # super().__init__("TOR", str(self.paths["encoding_table"]), "Tales-Of-Rebirth")
        
        with open(self.paths["encoding_table"], encoding="utf-8") as f:
            jsonRaw = json.load(f)

        for k, v in jsonRaw.items():
            self.jsonTblTags[k] = {int(k2, 16): v2 for k2, v2 in v.items()}
        
        for k, v in self.jsonTblTags.items():
            self.ijsonTblTags[k] = {v2: k2 for k2, v2 in v.items()}
        self.id = 1
        # byteCode
        self.story_byte_code = b"\xF8"
        self.string_opcode = InstructionType.STRING
        self.list_status_insertion: list[str] = ['Done', 'Proofreading', 'Editing']


    # Extract the story files
    def extract_all_story(self, replace=False) -> None:
        print("Extracting Story files...")

        folder_path = self.paths["story_xml"]
        folder_path.mkdir(exist_ok=True)
        scpk_path = self.paths["extracted_files"] / "DAT" / "SCPK"

        for file in tqdm(list(scpk_path.glob("*.scpk"))):
            theirsce = Theirsce(Scpk.from_path(file).rsce)
            xml_text = self.get_xml_from_theirsce(theirsce, "Story")
            self.id = 1
            
            with open(folder_path / file.with_suffix(".xml").name, "wb") as xml:
                xml.write(xml_text)

            
    # Extract all the skits files
    def extract_all_skits(self, replace=False) -> None:
        print("Extracting Skit files...")

        folder_path = self.paths["skit_xml"]
        folder_path.mkdir(exist_ok=True)
        pak2_path = self.paths["extracted_files"] / "DAT" / "PAK2"

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
    def bytes_to_text(self, src: FileIO, offset: int = -1) -> str:
        finalText = ""
        tags = self.jsonTblTags['TAGS']
        chars = self.jsonTblTags['TBL']

        if (offset > 0):
            src.seek(offset, 0)

        while True:
            b = src.read(1)
            if b == b"\x00": break

            b = ord(b)
            # Custom Encoded Text
            if (0x99 <= b <= 0x9F) or (0xE0 <= b <= 0xEB):
                c = (b << 8) | src.read_uint8()
                finalText += chars.get(c, "{%02X}{%02X}" % (c >> 8, c & 0xFF))
                continue
            
            if b == 0x1:
                finalText += ("\n")
                continue
            
            if b == 0x2:
                finalText += "<" + tags.get(b, f"{b:02X}") + ">"
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
                next_b = src.read(1)
                if next_b == b"\x40":
                    finalText += "　"
                else:
                    finalText += "{%02X}" % b
                    finalText += "{%02X}" % ord(next_b)
                continue
            
            # Simple Tags
            if 0x3 <= b <= 0xF:
                parameter = src.read_uint32()

                tag_name = tags.get(b, f"{b:02X}")
                tag_param = self.jsonTblTags.get(tag_name.upper(), {}).get(parameter, None)  

                if tag_param is not None:
                    finalText += f"<{tag_param}>"
                else:
                    finalText += f"<{tag_name}:{parameter:X}>"

                continue
            
            # Variable tags (same as above but using rsce bytecode as parameter)
            if 0x13 <= b <= 0x1A:
                tag_name = f"unk{b:02X}"
                parameter = "".join([f"{c:02X}" for c in Theirsce.read_tag_bytes(src)])
         
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
    

    def pack_all_skits(self):
        print("Recreating Skit files...")

        out_path = self.paths["temp_files"] / "DAT" / "PAK2"
        out_path.mkdir(parents=True, exist_ok=True)
        xml_path = self.paths["skit_xml"]
        pak2_path = self.paths["extracted_files"] / "DAT" / "PAK2"

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
        slps_path = self.paths["original_files"] / self.main_exe_name
        with open(slps_path, "rb") as elf:
            elf.seek(self.POINTERS_BEGIN, 0)
            blob = elf.read(self.POINTERS_END-self.POINTERS_BEGIN)
            
        pointers = struct.unpack(f"<{len(blob)//4}I", blob)
        file_data: list[tuple[int, int]] = []
        for c, n in zip(pointers, pointers[1:]):
            remainder = c & self.LOW_BITS
            start = c & self.HIGH_BITS
            end = (n & self.HIGH_BITS) - remainder
            file_data.append((start, end - start)) 
        
        return file_data

    # Extract the file DAT.BIN to the different directorties
    def extract_main_archive(self) -> None:
        dat_bin_path = self.paths["extracted_files"] / "DAT"
        
        self.clean_folder(dat_bin_path)

        print("Extracting DAT.BIN files...")
        with open(self.paths["original_files"] / "DAT.BIN", "rb") as f:
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
                
                final_path = dat_bin_path / extension.upper()
                final_path.mkdir(exist_ok=True)
        
                with open(final_path / fname, "wb") as output:
                    output.write(data)


    def get_style_pointers(self, file: FileIO, pointers_start: int, pointers_end: int, base_offset: int, style: str) -> tuple[list[int], list[int]]:

        file.seek(pointers_start)
        pointers_offset: list[int] = []
        pointers_value: list[int]  = []
        split: list[str] = [ele for ele in re.split(r'(P)|(\d+)', style) if ele]
        
        while file.tell() < pointers_end:
            for step in split:
                if step == "P":
                    off = file.read_uint32()
                    if base_offset < 0 and off == 0: continue
                    pointers_offset.append(file.tell() - 4)
                    pointers_value.append(base_offset + off)
                else:
                    file.read(int(step))
        
        return pointers_offset, pointers_value
    

    def extract_all_menu(self) -> None:
        print("Extracting Menu Files...")

        xml_path = self.paths["menu_xml"]
        xml_path.mkdir(exist_ok=True)

        # Read json descriptor file
        with open(self.paths["menu_table"], encoding="utf-8") as f:
            menu_json = json.load(f)

        for entry in tqdm(menu_json):

            if entry["file_path"] == "${main_exe}":
                file_path = self.paths["original_files"] / self.main_exe_name
            else:
                file_path = self.paths["extracted_files"] / entry["file_path"]

            if entry["is_pak"]:
                pak = Pak.from_path(file_path, int(entry["pak_type"]))

                for p_file in entry["files"]:
                    f_index = int(p_file["file"])
                    with FileIO(pak[f_index].data, "rb") as f:
                        xml_data = self.extract_menu_file(p_file, f)

                    with open(xml_path / f"{file_path.stem}_{f_index:04d}.xml", "wb") as xmlFile:
                        xmlFile.write(xml_data)

            else:
                with FileIO(file_path, "rb") as f:
                    xml_data = self.extract_menu_file(entry, f)

                with open(xml_path / f"{file_path.stem}.xml", "wb") as xmlFile:
                    xmlFile.write(xml_data)
            

    def extract_menu_file(self, file_def, f: FileIO):
        section_list = []
        pointers_offset_list = []
        texts_list = []

        base_offset = int(file_def["base_offset"])
        xml_root = etree.Element("MenuText")
        # print("BaseOffset:{}".format(base_offset))

        # Collect the canonical pointer for the embedded
        emb = dict()
        for pair in file_def["embedded"]:
            f.seek(pair["HI"][0] + base_offset)
            hi = f.read_uint16() << 0x10
            f.seek(pair["LO"][0] + base_offset)
            lo = f.read_int16()
            emb[(hi + lo) + base_offset] = [pair["HI"], pair["LO"]]

        for section in file_def['sections']:
            pointers_start = int(section["pointers_start"])
            pointers_end = int(section["pointers_end"])
            
            #Extract Pointers of the file
            # print("Extract Pointers")
            pointers_offset, pointers_value = self.get_style_pointers(f, pointers_start, pointers_end, base_offset, section['style'])
            # print([hex(pv) for pv in pointers_value])
        
            #Extract Text from the pointers
            # print("Extract Text")
            # texts = [ self.bytes_to_text(f, ele) for ele in pointers_value]
            
            #Make a list
            #section_list.append(section['section']) 
            #pointers_offset_list.extend(pointers_offset)
            #texts_list.extend( texts )
            temp = dict()
            for off, val in zip(pointers_offset, pointers_value):
                text = self.bytes_to_text(f, val)
                temp.setdefault(text, dict()).setdefault("ptr", []).append(off)
                    
                if val in emb:
                    temp[text]["emb"] = emb.pop(val, None)
    
            #Remove duplicates
            #list_informations = self.remove_duplicates(section_list, pointers_offset_list, texts)
            list_informations = [(k, str(v['ptr'])[1:-1], v.setdefault('emb', None)) for k, v in temp.items()]

            #Build the XML Structure with the information
            self.create_Node_XML(xml_root, list_informations, section['section'])

        # Write the embedded pointers section last
        temp = dict()
        for k, v in emb.items():
            text = self.bytes_to_text(f, k)
            temp[text] = dict()
            temp[text]["ptr"] = []
            temp[text]["emb"] = v

        #Remove duplicates
        #list_informations = self.remove_duplicates(section_list, pointers_offset_list, texts)
        list_informations = [(k, str(v['ptr'])[1:-1], v.setdefault('emb', None)) for k, v in temp.items()]

        #Build the XML Structure with the information
        self.create_Node_XML(xml_root, list_informations, "MIPS PTR TEXT")

        
        #Write to XML file
        return etree.tostring(xml_root, encoding="UTF-8", pretty_print=True)
        
    def pack_all_menu(self) -> None:
        print("Packing Menu Files...")

        xml_path = self.paths["menu_xml"]
        out_path = self.paths["temp_files"]

        # Read json descriptor file
        with open(self.paths["menu_table"], encoding="utf-8") as f:
            menu_json = json.load(f)

        for entry in tqdm(menu_json):

            if entry["file_path"] == "${main_exe}":
                file_path = self.paths["original_files"] / self.main_exe_name
            else:
                file_path = self.paths["extracted_files"] / entry["file_path"]

            if entry["is_pak"]:
                pak = Pak.from_path(file_path, int(entry["pak_type"]))

                
                for p_file in entry["files"]:
                    f_index = int(p_file["file"])
                    pools: list[list[int, int]] = [[x[0] + int(p_file["base_offset"]), x[1]-x[0]] for x in p_file["safe_areas"]] 
                    pools.sort(key=lambda x: x[1])
                    with open(xml_path / f"{file_path.stem}_{f_index:04d}.xml", "r", encoding='utf-8') as xmlFile:
                        root = etree.fromstring(xmlFile.read(), parser=etree.XMLParser(recover=True))
                    
                    with FileIO(pak[f_index].data, "rb") as f:
                        for line in root.iter("Entry"):
                            hi = []
                            lo = []
                            
                            flat_ptrs = []
                            poff = line.find("PointerOffset")
                            p = line.find("EmbedOffset")
                            if p is not None:
                                hi = [int(x) for x in p.find("hi").text.split(",")]
                                lo = [int(x) for x in p.find("lo").text.split(",")]
                            if poff.text is not None:
                                flat_ptrs = [int(x) for x in poff.text.split(",")]
                            
                            #Grab the fields from the Entry in the XML
                            status = line.find("Status").text
                            japanese_text = line.find("JapaneseText").text
                            english_text = line.find("EnglishText").text
                            
                            #Use the values only for Status = Done and use English if non empty
                            final_text = ''
                            if (status not in ['Problematic', 'To Do']):
                                final_text = english_text or japanese_text or ''
                            else:
                                final_text = japanese_text or ''
                            text_bytes = self.text_to_bytes(final_text) + b"\x00"

                            for pool in pools:
                                l = len(text_bytes)
                                if l <= pool[1]:
                                    str_pos = pool[0]
                                    pool[0] += l
                                    pool[1] -= l
                                    break
                            else:
                                raise ValueError("Ran out of space")
                            
                            f.seek(str_pos)
                            f.write(text_bytes)
                            virt_pos = str_pos + abs(int(p_file["base_offset"]))
                            for off in flat_ptrs:
                                f.seek(off)
                                f.write_uint32(virt_pos)
                            
                            for _h, _l in zip(hi, lo):
                                if virt_pos & 0xffff >= 0x8000:
                                    f.seek(_h + int(p_file["base_offset"]))
                                    f.write_uint16(((virt_pos >> 0x10) + 1) & 0xFFFF)
                                    f.seek(_l + int(p_file["base_offset"]))
                                    f.write_uint16(virt_pos & 0xFFFF)
                                else:
                                    f.seek(_h + int(p_file["base_offset"]))
                                    f.write_uint16(((virt_pos >> 0x10)) & 0xFFFF)
                                    f.seek(_l + int(p_file["base_offset"]))
                                    f.write_uint16(virt_pos & 0xFFFF)

                        f.seek(0)
                        pak[f_index].data = f.read()
                        # out_path.mkdir(parents=True, exist_ok=True)
                        # with open(out_path / f"dbg_{file_path.stem}_{f_index:04d}.bin", "wb") as g:
                        #     g.write(pak[f_index].data)

                (out_path / entry["file_path"]).parent.mkdir(parents=True, exist_ok=True)
                with open(out_path / entry["file_path"], "wb") as f:
                    f.write(pak.to_bytes(int(entry["pak_type"])))


            else:
                pools: list[list[int]] = [[x[0] + int(entry["base_offset"]), x[1]-x[0]] for x in entry["safe_areas"]] 
                pools.sort(key=lambda x: x[1])
                with open(xml_path / f"{file_path.stem}.xml", "r", encoding='utf-8') as xmlFile:
                    root = etree.fromstring(xmlFile.read(), parser=etree.XMLParser(recover=True))
                
                with open(file_path, "rb") as f:
                    file_b = f.read()
                
                with FileIO(file_b, "wb") as f:
                    for line in root.iter("Entry"):
                        hi = []
                        lo = []
                        
                        flat_ptrs = []
                        poff = line.find("PointerOffset")
                        p = line.find("EmbedOffset")
                        if p is not None:
                            hi = [int(x) for x in p.find("hi").text.split(",")]
                            lo = [int(x) for x in p.find("lo").text.split(",")]
                        if poff.text is not None:
                            flat_ptrs = [int(x) for x in poff.text.split(",")]
                        
                        #Grab the fields from the Entry in the XML
                        status = line.find("Status").text
                        japanese_text = line.find("JapaneseText").text
                        english_text = line.find("EnglishText").text
                        
                        #Use the values only for Status = Done and use English if non empty
                        final_text = ''
                        if (status not in ['Problematic', 'To Do']):
                            final_text = english_text or japanese_text or ''
                        else:
                            final_text = japanese_text or ''
                        text_bytes = self.text_to_bytes(final_text) + b"\x00"

                        for pool in pools:
                            l = len(text_bytes)
                            if l <= pool[1]:
                                str_pos = pool[0]
                                pool[0] += l
                                pool[1] -= l
                                break
                        else:
                            raise ValueError("Ran out of space")
                        
                        f.seek(str_pos)
                        f.write(text_bytes)
                        virt_pos = str_pos + abs(int(entry["base_offset"]))
                        for off in flat_ptrs:
                            f.seek(off)
                            f.write_uint32(virt_pos)
                        
                        for _h, _l in zip(hi, lo):
                            if virt_pos & 0xffff >= 0x8000:
                                f.seek(_h + int(entry["base_offset"]))
                                f.write_uint16(((virt_pos >> 0x10) + 1) & 0xFFFF)
                                f.seek(_l + int(entry["base_offset"]))
                                f.write_uint16(virt_pos & 0xFFFF)
                            else:
                                f.seek(_h + int(entry["base_offset"]))
                                f.write_uint16(((virt_pos >> 0x10)) & 0xFFFF)
                                f.seek(_l + int(entry["base_offset"]))
                                f.write_uint16(virt_pos & 0xFFFF)

                    f.seek(0)
                    (out_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(out_path / file_path.name, "wb") as g:
                        g.write(f.read())
                    # out_path.mkdir(parents=True, exist_ok=True)
                    # with open(out_path / f"dbg_{file_path.stem}_{f_index:04d}.bin", "wb") as g:
                    #     g.write(pak[f_index].data)


    def create_Node_XML(self, root, list_informations, section) -> None:
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = section

        for text, pointers_offset, emb in list_informations:
            self.create_Entry(strings_node,  pointers_offset, text, emb)

        
    def pack_main_archive(self):
        sectors: list[int] = [0]
        remainders: list[int] = []
        buffer = 0

        # Copy the original SLPS to Disc/New
        # shutil.copy(self.elf_original, self.elf_new)
   
        print("Packing DAT.BIN files...")
        output_dat_path = self.paths["final_files"] / "DAT.BIN"
        original_files = self.paths["extracted_files"] / "DAT"
        total_files = (self.POINTERS_END - self.POINTERS_BEGIN) // 4
    
            
        # Get all original DAT.BIN files
        file_list: dict[int, Path] = {}
        for file in original_files.glob("*/*"):
            file_index = int(file.name[:5])
            file_list[file_index] = file

        # Overlay whatever we have compiled
        # file_list: dict[int, Path] = {}
        for file in (self.paths["temp_files"] / "DAT").glob("*/*"):
            file_index = int(file.name[:5])
            file_list[file_index] = file
                
        with open(output_dat_path, "wb") as output_dat:
            for i in tqdm(range(total_files)):
                file = file_list.get(i)
                if not file:
                    remainders.append(0); sectors.append(buffer)
                    continue

                with open(file, "rb") as f2:
                    data = f2.read()
                
                comp_type = re.search(self.VALID_FILE_NAME, file.name).group(2)
                if comp_type != None:
                    data = comptolib.compress_data(data, version=int(comp_type))
            
                output_dat.write(data)
                size = len(data)
                remainder = 0x40 - (size % 0x40)
                if remainder == 0x40: remainder = 0
                output_dat.write(b"\x00" * remainder)
              
        
                remainders.append(remainder)
                buffer += size + remainder
                sectors.append(buffer)
        
        #Use the new SLPS updated and update the pointers for the SCPK
        # original_slps = self.paths["original_files"] / self.main_exe_name
        original_slps = self.paths["temp_files"] / self.main_exe_name
        patched_slps = self.paths["final_files"] / self.main_exe_name
        with open(original_slps, "rb") as f:
            slps = f.read()

        with open(patched_slps, "wb") as f:
            f.write(slps)
            f.seek(self.POINTERS_BEGIN)
            for sector, remainder in zip(sectors, remainders):
                f.write(struct.pack("<I", sector + remainder))
        
    
        
    def pack_all_story(self):
        print("Recreating Story files...")

        out_path = self.paths["temp_files"] / "DAT" / "SCPK"
        out_path.mkdir(parents=True, exist_ok=True)
        xml_path = self.paths["story_xml"]
        scpk_path = self.paths["extracted_files"] / "DAT" / "SCPK"

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


    def extract_Iso(self, umd_iso: Path) -> None:  

        print("Extracting ISO files...")
        
        iso = pycdlib.PyCdlib()
        iso.open(str(umd_iso))

        extract_to = self.paths["original_files"]
        self.clean_folder(extract_to)

        files = []
        for dirname, _, filelist in iso.walk(iso_path="/"):
            files += [dirname + x for x in filelist]
                
        for file in files:   
            out_path = extract_to / file[1:]   
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            with iso.open_file_from_iso(iso_path=file) as f, open(str(out_path).split(";")[0], "wb+") as output:
                with tqdm(total=f.length(), desc=f"Extracting {file[1:].split(';')[0]}", unit="B", unit_divisor=1024, unit_scale=True) as pbar:
                    while data := f.read(2048):
                        output.write(data)
                        pbar.update(len(data))

        iso.close()


    def clean_folder(self, path: Path) -> None:
        target_files = list(path.iterdir())
        if len(target_files) != 0:
            print("Cleaning folder...")
            for file in target_files:
                if file.is_dir():
                    shutil.rmtree(file)
                elif file.name.lower() != ".gitignore":
                    file.unlink(missing_ok=False)