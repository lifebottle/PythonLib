import datetime
import re
import shutil
import struct
import subprocess
import types
import os
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import tee
from pathlib import Path

import lxml.etree as etree
import pycdlib
import pyjson5 as json
from dulwich import line_ending, porcelain
from tqdm import tqdm
import io

import pythonlib.formats.pak2 as pak2lib
import pythonlib.utils.comptolib as comptolib
from pythonlib.formats.FileIO import FileIO
from pythonlib.formats.pak import Pak
from pythonlib.formats.scpk import Scpk
from pythonlib.formats.theirsce import Theirsce
from pythonlib.formats.theirsce_instructions import (AluOperation,
                                                     InstructionType,
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


# Bandage method to override autocrlf settings for peple without git
def get_blob_normalizer_custom(self):
    """Return a BlobNormalizer object."""
    git_attributes = {}
    config_stack = self.get_config_stack()
    config_stack.set("core", "autocrlf", "true")
    try:
        tree = self.object_store[self.refs[b"HEAD"]].tree
        return line_ending.TreeBlobNormalizer(
            config_stack,
            git_attributes,
            self.object_store,
            tree,
        )
    except KeyError:
        return line_ending.BlobNormalizer(config_stack, git_attributes)


class ToolsTOR(ToolsTales):
    
    POINTERS_BEGIN = 0xD76B0                                            # Offset to DAT.BIN pointer list start in SLPS_254.50 file
    POINTERS_END   = 0xE60C8                                            # Offset to DAT.BIN pointer list end in SLPS_254.50 file
    HIGH_BITS      = 0xFFFFFFC0
    LOW_BITS       = 0x3F

    
    def __init__(self, project_file: Path, insert_mask: list[str], changed_only: bool = False) -> None:
        base_path = project_file.parent
        self.jsonTblTags = {}
        self.ijsonTblTags = {}
        with open(project_file, encoding="utf-8") as f:
            jsonRaw = json.load(f)

        self.paths: dict[str, Path] = {k: base_path / v for k, v in jsonRaw["paths"].items()}
        self.main_exe_name = jsonRaw["main_exe_name"]
        self.asm_file = jsonRaw["asm_file"]

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
        self.list_status_insertion: list[str] = ['Done']
        self.list_status_insertion.extend(insert_mask)
        self.changed_only = changed_only
        self.repo_path = str(base_path)


    def get_repo_fixed(self):
        r = porcelain.Repo(self.repo_path)
        r.get_blob_normalizer = types.MethodType(get_blob_normalizer_custom, r)
        return r


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
            if b == b"": break

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
    
    def read_xml(self, xml_path: Path) -> etree._Element:
        with xml_path.open("r", encoding='utf-8') as xml_file:
            xml_str = xml_file.read().replace("<EnglishText></EnglishText>", "<EnglishText empty=\"true\"></EnglishText>")
        root = etree.fromstring(xml_str, parser=etree.XMLParser(recover=True))
        return root

    def get_node_bytes(self, entry_node) -> bytes:
        
        #Grab the fields from the Entry in the XML
        status = entry_node.find("Status").text
        japanese_text = entry_node.find("JapaneseText").text
        english_text = entry_node.find("EnglishText").text

        # ElementTree saves self-closing nodes for empty strings ('')
        # as such, japanese lines that are None are in fact just ''.
        # For english lines however None means "use Japanese line"
        # so honor that detail here

        final_text = japanese_text or ''
        if (status in self.list_status_insertion and english_text is not None):
            final_text = english_text
        elif entry_node.find("EnglishText").attrib.get("empty"):
            final_text = ""
        
        voiceId_node = entry_node.find("VoiceId")
        if (voiceId_node is not None):
            final_text = '<voice:{}>'.format(voiceId_node.text) + final_text
            
        #Convert the text values to bytes using TBL, TAGS, COLORS, ...
        bytes_entry = self.text_to_bytes(final_text)
        
        return bytes_entry
    
    
    def get_new_theirsce(self, theirsce: Theirsce, xml: Path) -> Theirsce:
        
        #To store the new text_offset and pointers to update
        new_text_offsets = dict()
              
        #Read the XML for the corresponding THEIRSCE
        root = self.read_xml(xml)
        # root = tree.getroot()

        #Go at the start of the dialog
        #Loop on every Entry and reinsert
        theirsce.seek(theirsce.strings_offset + 1)
        theirsce.truncate()
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

        in_list = []
        if self.changed_only:
            for item in porcelain.status(self.get_repo_fixed()).unstaged: # type: ignore
                item_path = Path(item.decode("utf-8"))
                if item_path.parent.name == "skits":
                    in_list.append(pak2_path / item_path.with_suffix(".3.pak2").name)
            if len(in_list) == 0:
                print("No changed files to insert...")
                return
        else:
            in_list = list(pak2_path.glob("*.pak2"))

        for file in (pbar := tqdm(in_list)):
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
        dat_bin_path.mkdir(exist_ok=True)
        
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


    def get_style_pointers(self, file: FileIO, ptr_range: tuple[int, int], base_offset: int, style: str) -> tuple[list[int], list[int]]:

        file.seek(ptr_range[0])
        pointers_offset: list[int] = []
        pointers_value: list[int]  = []
        split: list[str] = [ele for ele in re.split(r'([PT])|(\d+)', style) if ele]
        
        while file.tell() < ptr_range[1]:
            for step in split:
                if step == "P":
                    off = file.read_uint32()
                    if base_offset == 0 and off == 0: 
                        continue
                    pointers_offset.append(file.tell() - 4)
                    pointers_value.append(off - base_offset)
                elif step == "T":
                    off = file.tell()
                    pointers_offset.append(off)
                    pointers_value.append(off)
                else:
                    file.read(int(step))
        
        return pointers_offset, pointers_value
    

    def extract_all_menu(self) -> None:
        print("Extracting Menu Files...")

        xml_path = self.paths["menu_xml"]
        xml_path.mkdir(exist_ok=True)

        # Read json descriptor file
        with open(self.paths["menu_table"], encoding="utf-8") as f:
            menu_json = json.load(f) # type: ignore

        for entry in tqdm(menu_json):

            if entry["file_path"] == "${main_exe}":
                file_path = self.paths["original_files"] / self.main_exe_name
            else:
                file_path = self.paths["extracted_files"] / entry["file_path"]

            if entry["is_pak"]:
                pak = Pak.from_path(file_path, int(entry["pak_type"]))

                for p_file in entry["files"]:
                    f_index = int(p_file["file"])
                    if p_file["is_sce"]:
                        theirsce = Theirsce(pak[f_index].data)
                        xml_text = self.get_xml_from_theirsce(theirsce, "Story")
                        self.id = 1
                        
                        with open(xml_path / (p_file["friendly_name"] + ".xml"), "wb") as xml:
                            xml.write(xml_text)
                    else:
                        with FileIO(pak[f_index].data, "rb") as f:
                            self.extract_menu_file(xml_path, p_file, f)
            else:
                with FileIO(file_path, "rb") as f:
                    self.extract_menu_file(xml_path, entry, f)

            self.id = 1
            

    def extract_menu_file(self, xml_path: Path, file_def, f: FileIO) -> None:

        base_offset = file_def["base_offset"]
        xml_root = etree.Element("MenuText")

        # Collect the canonical pointer for the embedded pairs
        emb = dict()
        for pair in file_def["embedded"]:
            f.seek(pair["HI"][0] - base_offset)
            hi = f.read_uint16() << 0x10
            f.seek(pair["LO"][0] - base_offset)
            lo = f.read_int16()
            if ((hi + lo) - base_offset) in emb:
                emb[(hi + lo) - base_offset][0].append(*pair["HI"])
                emb[(hi + lo) - base_offset][1].append(*pair["LO"])
            else:
                emb[(hi + lo) - base_offset] = [pair["HI"], pair["LO"]]

        for section in file_def['sections']:
            max_len = 0
            pointers_start = int(section["pointers_start"])
            pointers_end = int(section["pointers_end"])
            
            # Extract Pointers list out of the file
            pointers_offset, pointers_value = self.get_style_pointers(f, (pointers_start, pointers_end), base_offset, section['style'])
            
            # Make a list, we also merge the emb pointers with the 
            # other kind in the case they point to the same text
            temp = dict()
            for off, val in zip(pointers_offset, pointers_value):
                text = self.bytes_to_text(f, val)
                temp.setdefault(text, dict()).setdefault("ptr", []).append(off)
                    
                if val in emb:
                    temp[text]["emb"] = emb.pop(val, None)
    
            # Remove duplicates
            list_informations = [(k, str(v['ptr'])[1:-1], v.setdefault('emb', None)) for k, v in temp.items()]

            # Build the XML Structure with the information
            if section['style'][0] == "T":
                max_len = int(section['style'][1:])
            self.create_Node_XML(xml_root, list_informations, section['section'], max_len)

            if file_def["split_sections"]:
                file_name = file_def["friendly_name"] + "_" + section["section"].replace(" ", "_") + ".xml"
                with open(xml_path / file_name, "wb") as xmlFile:
                    xmlFile.write(etree.tostring(xml_root, encoding="UTF-8", pretty_print=True))
                xml_root = etree.Element("MenuText")

        # Write the embedded pointers section last
        temp = dict()
        for k, v in emb.items():
            text = self.bytes_to_text(f, k)
            if text not in temp:
                temp[text] = dict()
                temp[text]["ptr"] = []
            
            if "emb" in temp[text]:
                temp[text]["emb"][0].append(*v[0])
                temp[text]["emb"][1].append(*v[1])
            else:
                temp[text]["emb"] = v

        #Remove duplicates
        #list_informations = self.remove_duplicates(section_list, pointers_offset_list, texts)
        list_informations = [(k, str(v['ptr'])[1:-1], v.setdefault('emb', None)) for k, v in temp.items()]

        #Build the XML Structure with the information
        if len(list_informations) != 0:
            if file_def["split_sections"]:
                xml_root = etree.Element("MenuText")
            self.create_Node_XML(xml_root, list_informations, "MIPS PTR TEXT")

        #Write to XML file
        # return etree.tostring(xml_root, encoding="UTF-8", pretty_print=True)
        if file_def["split_sections"]:
            file_name = file_def["friendly_name"] + "_MIPS_PTR.xml"
            with open(xml_path / file_name, "wb") as xmlFile:
                xmlFile.write(etree.tostring(xml_root, encoding="UTF-8", pretty_print=True))
        else:
            file_name = file_def["friendly_name"] + ".xml"
            with open(xml_path / file_name, "wb") as xmlFile:
                xmlFile.write(etree.tostring(xml_root, encoding="UTF-8", pretty_print=True))


    def get_menu_file_paths(self, entry: dict) -> tuple[Path, Path]:
        if entry["file_path"] == "${main_exe}":
            file_path = self.paths["original_files"] / self.main_exe_name
            stem = self.main_exe_name
        else:
            file_path = self.paths["extracted_files"] / entry["file_path"]
            stem = entry["file_path"]
        return file_path, Path(stem)
    
    def merge_split_menu_files(self, entry: dict, xml_folder_path: Path) -> etree._Element:
        names = []

        for section in entry["sections"]:
            names.append(f"{entry['friendly_name']}_{section['section'].replace(' ', '_')}.xml")
        
        if len(entry["embedded"]) != 0:
            names.append(entry["friendly_name"] + "_MIPS_PTR.xml")

        root = etree.Element("merged")
        insertion_point = etree.SubElement(root, "Strings")
        for name in names:
            data = self.read_xml(xml_folder_path / name)
            insertion_point.extend(data.iterfind("./Strings"))
        
        return root
    
    def get_new_menu(self, entry: dict, blob: FileIO, xml_folder_path: Path):
        base_offset = entry["base_offset"]
        
        # Create pools of valid free spots
        pools: list[list[int]] = [[x[0] - base_offset, x[1]-x[0]] for x in entry["safe_areas"]] 
        pools.sort(key=lambda x: x[1])

        if entry.get("split_sections", False):
            root = self.merge_split_menu_files(entry, xml_folder_path)
        else:
            xml_path = xml_folder_path / (entry["friendly_name"] + ".xml")
            root = self.read_xml(xml_path)

        self.pack_menu_file(root, pools, base_offset, blob, entry["friendly_name"] == "mnu_monster")
        blob.seek(0)
        return blob.read()

    
    def pack_all_menu(self) -> None:
        print("Packing Menu Files...")
        xml_folder_path: Path = self.paths["menu_xml"]
        out_path: Path = self.paths["temp_files"]

        # Read json descriptor file
        with open(self.paths["menu_table"], encoding="utf-8") as f:
            menu_json = json.load(f) # type: ignore

        for entry in (pbar := tqdm(menu_json)):
            file_path, file_relpath = self.get_menu_file_paths(entry)

            if entry["is_pak"]:
                pak = Pak.from_path(file_path, entry["pak_type"])
                out_folder = out_path / file_relpath.with_suffix("")
                
                for p_file in entry["files"]:
                    pbar.set_description_str(p_file["friendly_name"])
                    f_index = p_file["file"]
                    dest_path = out_folder / f"{f_index:04d}.bin"

                    if p_file["is_sce"]:
                        old_rsce = Theirsce(pak[f_index].data)
                        xml_name = xml_folder_path / (p_file["friendly_name"] + ".xml")
                        new_rsce = self.get_new_theirsce(old_rsce, xml_name)
                        new_rsce.seek(0)
                        data = new_rsce.read()
                    else:
                        with FileIO(pak[f_index].data, "r+b") as f:
                            data = self.get_new_menu(p_file, f, xml_folder_path)

            else:
                dest_path = out_path / file_relpath
                with FileIO(file_path, "r+b") as f:
                    data = self.get_new_menu(entry, f, xml_folder_path)

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with dest_path.open("wb") as f:
                f.write(data)


    def pack_menu_file(self, root, pools: list[list[int]], base_offset: int, f: FileIO, monster_hack: bool) -> None:
        limit_reached = False
        out_file = f
        vbase_offset = base_offset
        mode = "wb" if monster_hack else "a"
        seen_strings: dict[bytes, int] = dict()

        with FileIO(self.paths["temp_files"] / "DAT/BIN/10264.bin", mode) as monster_file:
            for line in root.iter("Entry"):
                hi = []
                lo = []
                flat_ptrs = []

                p = line.find("EmbedOffset")
                if p is not None:
                    hi = [int(x) - base_offset for x in p.find("hi").text.split(",")]
                    lo = [int(x) - base_offset for x in p.find("lo").text.split(",")]

                poff = line.find("PointerOffset")
                if poff.text is not None:
                    flat_ptrs = [int(x) for x in poff.text.split(",")]

                mlen = line.find("MaxLength")
                if mlen is not None:
                    max_len = int(mlen.text)
                    out_file.seek(flat_ptrs[0])
                    text_bytes = self.get_node_bytes(line) + b"\x00"
                    if len(text_bytes) > max_len:
                        tqdm.write(f"Line id {line.find('Id').text} ({line.find('JapaneseText').text}) too long, truncating...")
                        out_file.write(text_bytes[:max_len-1] + b"\x00")
                    else:
                        out_file.write(text_bytes + (b"\x00" * (max_len-len(text_bytes))))
                    continue
                
                text_bytes = self.get_node_bytes(line) + b"\x00"

                if not limit_reached:
                    for pool in pools:
                        ln = len(text_bytes)
                        if ln <= pool[1]:
                            str_pos = pool[0]
                            if text_bytes not in seen_strings:
                                pool[0] += ln
                                pool[1] -= ln
                            break
                    else:
                        if monster_hack:
                            limit_reached = True
                            out_file = monster_file
                            str_pos = 0
                            vbase_offset = 0x00391400
                        else:
                            raise ValueError("Ran out of space")
                
                if text_bytes in seen_strings:
                    virt_pos = seen_strings[text_bytes]
                else:
                    out_file.seek(str_pos)
                    out_file.write(text_bytes)
                    virt_pos = str_pos + vbase_offset
                    seen_strings[text_bytes] = str_pos + vbase_offset

                if limit_reached:
                    if str_pos >= 0x19000:
                        raise ValueError("mnu_monster too big, again!")
                    str_pos += len(text_bytes)

                for off in flat_ptrs:
                    f.write_uint32_at(off, virt_pos)
                
                for _h, _l in zip(hi, lo):
                    val_hi = (virt_pos >> 0x10) & 0xFFFF
                    val_lo = (virt_pos) & 0xFFFF
                    
                    # can't encode the lui+addiu directly
                    if val_lo >= 0x8000:
                        val_hi += 1

                    f.write_uint16_at(_h, val_hi)
                    f.write_uint16_at(_l, val_lo)


    def patch_binaries(self):
        bin_path = self.paths["tools"] / "bin"
        cc_path = self.paths["tools"] / "bin" / "cc" / "bin"
        dll_path = self.paths["tools"] / "bin" / "dll"
        env = os.environ.copy()
        env["PATH"] = f"{bin_path.as_posix()};{cc_path.as_posix()};{dll_path.as_posix()};{env['PATH']}"
        r = subprocess.run(
            [
                str(self.paths["tools"] / "bin" / "make.exe"),
            ],
            env=env,
            cwd=str(self.paths["tools"] / "hacks")
        )
        if r.returncode != 0:
            raise ValueError("Error building code")
        r = subprocess.run(
            [
                str(self.paths["tools"] / "hacks" / "armips.exe"),
                str(self.paths["tools"] / "hacks" / self.asm_file),
                "-strequ",
                "__SLPS_PATH__", 
                str(self.paths["temp_files"] / self.main_exe_name),
                "-strequ",
                "__BTL_OVL_PATH__", 
                str(self.paths["temp_files"] / "DAT" / "PAK3" / "00013" / "0000.bin"),
                "-strequ",
                "__3DFIELD_OVL_PATH__", 
                str(self.paths["temp_files"] / "DAT" / "PAK3" / "00013" / "0002.bin"),
                "-strequ",
                "__MNU_NAME_OVL_PATH__", 
                str(self.paths["temp_files"] / "DAT" / "OVL" / "11224.ovl"),
                "-strequ",
                "__MNU_STATUS_OVL_PATH__", 
                str(self.paths["temp_files"] / "DAT" / "OVL" / "11216.ovl"),
                "-strequ",
                "__MNU_MONSTER_OVL_PATH__", 
                str(self.paths["temp_files"] / "DAT" / "OVL" / "11217.ovl"),
            ],
            env=env,
            cwd=str(self.paths["tools"] / "hacks")
        )
        if r.returncode != 0:
            raise ValueError("Error running armips")


    def create_Node_XML(self, root, list_informations, section, max_len = 0) -> None:
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = section

        for text, pointers_offset, emb in list_informations:
            self.create_Entry(strings_node, pointers_offset, text, emb, max_len)

        
    def pack_main_archive(self):
        sectors: list[int] = [0]
        remainders: list[int] = []

        # Copy the original SLPS to Disc/New
        # shutil.copy(self.elf_original, self.elf_new)
   
        print("Packing DAT.BIN files...")
        output_dat_path = self.paths["final_files"] / "DAT.BIN"
        total_files = (self.POINTERS_END - self.POINTERS_BEGIN) // 4
                
        with open(output_dat_path, "wb") as output_dat:
            for blob in tqdm(self._pack_dat_iter(sectors, remainders), total=total_files, desc="Inserting DAT.BIN"):
                output_dat.write(blob)
        
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


    def _pack_dat_iter(self, sectors: list[int], remainders: list[int]) -> Iterable[tuple[bytes, int]]:
        buffer = 0
        original_files = self.paths["extracted_files"] / "DAT"
        total_files = ((self.POINTERS_END - self.POINTERS_BEGIN) // 4) - 1

        ######
        original_data = self.get_datbin_file_data()
    
            
        # Get all original DAT.BIN files
        file_list: dict[int, Path] = {}
        # for file in original_files.glob("*/*"):
        #     file_index = int(file.name[:5])
        #     file_list[file_index] = file

        # Overlay whatever we have compiled
        for file in (self.paths["temp_files"] / "DAT").glob("*/*"):
            file_index = int(file.name[:5])
            if file_index in file_list and file_list[file_index].is_dir():
                continue
            else:
                file_list[file_index] = file

        max_chunk_size = 0x1000000
        
        with open(self.paths["original_files"] / "DAT.BIN", "rb") as datbin:
            i = 0
            while i < total_files:
                start_index = i

                current_chunk_size = 0
                while i < total_files:
                    if file_list.get(i):
                        break
                    size = original_data[i][1]
                    remainder = 0x40 - (size % 0x40)
                    if remainder == 0x40:
                        remainder = 0

                    size += remainder

                    if current_chunk_size + size > max_chunk_size:
                        break

                    current_chunk_size += size
                    remainders.append(remainder)
                    buffer += size
                    sectors.append(buffer)
                    i += 1

                if start_index != i:
                    datbin.seek(original_data[start_index][0])
                    blob = datbin.read(current_chunk_size)
                    yield blob, i - start_index
                    continue

                file = file_list[i]
                # if not file:
                #     remainders.append(0)
                #     sectors.append(buffer)
                #     i += 1
                #     yield b"", 1
                #     continue

                data = b""
                if file.is_dir():
                    if file.parent.stem == "SCPK":
                        scpk_path = original_files / "SCPK" / (file.name + ".scpk")
                        scpk_o = Scpk.from_path(scpk_path)
                        with open(file / (file.stem + ".rsce"), "rb") as f:
                            scpk_o.rsce = f.read()
                        data = scpk_o.to_bytes()
                        comp_type = re.search(self.VALID_FILE_NAME, scpk_path.name).group(2)
                    elif file.parent.stem == "PAK3":
                        pak_path = original_files / "PAK3" / (file.name + ".pak3")
                        pak_o = Pak.from_path(pak_path, 3)
                        for pak_file in file.glob("*.bin"):
                            file_index = int(pak_file.name.split(".bin")[0])
                            with open(pak_file, "rb") as pf:
                                pak_o.files[file_index].data = pf.read()
                        data = pak_o.to_bytes(3)
                        comp_type = re.search(self.VALID_FILE_NAME, pak_path.name).group(2)
                    if file.parent.stem == "PAK1":
                        pak_path = original_files / "PAK1" / (file.name + ".pak1")
                        pak_o = Pak.from_path(pak_path, 1)
                        for pak_file in file.glob("*.bin"):
                            file_index = int(pak_file.name.split(".bin")[0])
                            with open(pak_file, "rb") as pf:
                                pak_o.files[file_index].data = pf.read()
                        data = pak_o.to_bytes(1)
                        comp_type = re.search(self.VALID_FILE_NAME, pak_path.name).group(2)
                    if file.parent.stem == "PAK0":
                        pak_path = original_files / "PAK0" / (file.name + ".pak0")
                        pak_o = Pak.from_path(pak_path, 0)
                        for pak_file in file.glob("*.bin"):
                            file_index = int(pak_file.name.split(".bin")[0])
                            with open(pak_file, "rb") as pf:
                                pak_o.files[file_index].data = pf.read()
                        data = pak_o.to_bytes(0)
                        comp_type = re.search(self.VALID_FILE_NAME, pak_path.name).group(2)
                else:
                    with open(file, "rb") as f2:
                        data = f2.read()
                    comp_type = re.search(self.VALID_FILE_NAME, file.name).group(2)
                
                if comp_type is not None:
                    data = comptolib.compress_data(data, version=int(comp_type))
            
                size = len(data)
                remainder = 0x40 - (size % 0x40)
                if remainder == 0x40:
                    remainder = 0
        
                remainders.append(remainder)
                buffer += size + remainder
                sectors.append(buffer)
                i += 1
                yield data + (b"\x00" * remainder), 1

    def get_xml_from_list(self, lines: list[tuple[int, str]], section: str) -> bytes:

        root = etree.Element("SceneText")
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = section
        
        for line in lines:
            entry_node = etree.SubElement(strings_node, "Entry")
            etree.SubElement(entry_node,"PointerOffset").text = str(line[0])

            text_split = list(filter(None, re.split(self.COMMON_TAG, line[1])))
            
            if len(text_split) > 1 and text_split[0].startswith("<voice:"):
                etree.SubElement(entry_node,"VoiceId").text  = text_split[0][1:-1].split(":")[1]
                etree.SubElement(entry_node, "JapaneseText").text = ''.join(text_split[1:])
            else:
                etree.SubElement(entry_node, "JapaneseText").text = line[1]
            
            etree.SubElement(entry_node,"EnglishText")
            etree.SubElement(entry_node,"Notes")
            etree.SubElement(entry_node,"Id").text = str(self.id)
            
            self.id = self.id + 1
            
            if line[1] == '':
                statusText = 'Done'
            else:
                statusText = 'To Do'
            etree.SubElement(entry_node,"Status").text = statusText
        
        # Return XML string
        return etree.tostring(root, encoding="UTF-8", pretty_print=True)

    def extract_all_minigame(self, replace=False) -> None:
        print("Extracting Minigame files...")

        valid_sfm2 = [ 
            1, 17, 30, 31, 34, 36, 37, 38, 
            39, 40, 41, 42, 43, 45, 48, 53, 61
        ]

        folder_path = self.paths["translated_files"] / "minigame"
        folder_path.mkdir(exist_ok=True)
        pak3_path = self.paths["extracted_files"] / "DAT" / "PAK3" / "00023.pak3"

        minigame_pak = Pak.from_path(pak3_path, 3)
        for index in tqdm(valid_sfm2):
            self.id = 0
            sfm = minigame_pak.files[index].data

            lines = []
            
            with FileIO(sfm, "rb") as f:
                # special case
                if index == 45:
                    tbl_off = f.read_int32_at(0x20)
                    f.seek(tbl_off)
                    offsets = struct.unpack("<14I", f.read(0x38))[1::2]

                    for off in offsets:
                        lines.append((off, self.bytes_to_text(f, tbl_off + off))) # fake offset
                    
                code_off = f.read_int32_at(0x18)
                code_end = code_off + f.read_int32_at(0xC)
                text_off = f.read_int32_at(0x1C)

                f.seek(code_off)
                while f.tell() < code_end:
                    b = f.read_int8()
                    len = (b >> 4) & 0xF
                    opcode = b & 0xF

                    # is it the load string opcode?
                    if opcode == 7:
                        if f.read_int8() == 2:
                            off = f.tell()
                            if len == 3:
                                str_off = f.read_uint8()
                            elif len == 4:
                                str_off = f.read_uint16()
                            else:
                                raise ValueError

                            save = f.tell()
                            lines.append((off, self.bytes_to_text(f, str_off + text_off)))
                            f.seek(save)
                        else:
                            f.read(len - 2)
                    else:
                        f.read(len - 1)

            
            xml_text = self.get_xml_from_list(lines, "Minigame")
            
            xml_name = f"{index:04d}.xml"
            with open(folder_path / xml_name, "wb") as xml:
                xml.write(xml_text.replace(b"\n", b"\r\n"))


    def pack_all_minigame(self):
        print("Recreating Minigame files...")

        valid_sfm2 = [ 
            1, 17, 30, 31, 34, 36, 37, 38, 
            39, 40, 41, 42, 43, 45, 48, 53, 61
        ]
        
        pak3_path = self.paths["extracted_files"] / "DAT" / "PAK3" / "00023.pak3"
        out_path = self.paths["temp_files"] / "DAT" / "SCPK" / "00023"
        out_path.mkdir(parents=True, exist_ok=True)

        minigame_pak = Pak.from_path(pak3_path, 3)
        for index in tqdm(valid_sfm2):
            
            sfm = minigame_pak.files[index].data

            with FileIO(sfm, "rb") as f:                
                new_text_offsets = dict()
                root = self.read_xml(folder_path / f"{index:04d}.xml")
                text_off = f.read_int32_at(0x1C)
                tbl_off = f.read_int32_at(0x20) + 4
                f.seek(text_off)
                f.truncate()

                nodes = [ele for ele in root.iter('Entry')]
                nodes = [ele for ele in nodes if ele.find('PointerOffset').text != "-1"]

                for entry_node in nodes:
                    new_text_offsets[entry_node.find("PointerOffset").text] = f.tell()
                    bytes_entry = self.get_node_bytes(entry_node)
                    f.write(bytes_entry + b'\x00')
                
                for i, (pointer, text_offset) in enumerate(new_text_offsets.items()):
                    new_value = text_offset - text_off

                    if index == 45 and i < 7:
                        f.write_uint32_at(tbl_off + (i * 8), new_value + 0x54)
                    else:
                        f.seek(int(pointer) - 2)
                        len = (f.read_uint8() >> 4) & 0xF
                        if len == 3:
                            f.write(struct.pack("<B", new_value))
                        elif len == 4:
                            f.write(struct.pack("<H", new_value))
                        else:
                            raise ValueError

                f.seek(0, io.SEEK_END)
                file_size = f.tell()
                f.write_uint32_at(0x8, file_size)
                f.write_uint32_at(0x10, file_size - text_off)

                f.seek(0)
                with open(out_path / f"{index:04d}.bin", "wb") as o:
                    o.write(f.read())


    def pack_all_story(self):
        print("Recreating Story files...")

        out_path = self.paths["temp_files"] / "DAT" / "SCPK"
        out_path.mkdir(parents=True, exist_ok=True)
        xml_path = self.paths["story_xml"]
        scpk_path = self.paths["extracted_files"] / "DAT" / "SCPK"

        # Collect available anp3's
        anp3_path = self.paths["translated_files"] / "graphic"

        anp3s: dict[str, tuple[int, bytes]] = dict()

        for anp3 in anp3_path.glob("*.anp3"):
            with anp3.open("rb") as f:
                anp3s[anp3.stem[:5]] = (int(anp3.stem[6:8]), f.read())

        in_list = []
        if self.changed_only:
            for item in porcelain.status(self.get_repo_fixed()).unstaged: # type: ignore
                item_path = Path(item.decode("utf-8"))
                if item_path.parent.name == "story":
                    in_list.append(scpk_path / item_path.with_suffix(".scpk").name)
            if len(in_list) == 0:
                print("No changed files to insert...")
                return
        else:
            in_list = list(scpk_path.glob("*.scpk"))

        for file in (pbar:= tqdm(in_list)):
            pbar.set_description_str(file.name)
            curr_scpk = Scpk.from_path(file)
            old_rsce = Theirsce(curr_scpk.rsce)
            new_rsce = self.get_new_theirsce(old_rsce, xml_path / file.with_suffix(".xml").name)
            new_rsce.seek(0)
            curr_scpk.rsce = new_rsce.read()

            # insert anp3 (if applicable)
            scpk_name = file.stem[:5]
            if scpk_name in anp3s:
                char_id = curr_scpk.char_ids[anp3s[scpk_name][0] - 2] # the -2 is to account for the map and chrid "files"
                curr_scpk.chars[char_id].files[0].data = anp3s[scpk_name][1]
            
            with open(out_path / file.name, "wb") as f:
                f.write(curr_scpk.to_bytes())

            
    def insert_All(self):
        
        #Updates SCPK based on XMLs data
        
        self.pack_main_archive()


    def extract_Iso(self, game_iso: Path) -> None:  

        print("Extracting ISO files...")
        
        iso = pycdlib.PyCdlib() # type: ignore
        iso.open(str(game_iso))

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
                    while data := f.read(0x8000):
                        output.write(data)
                        pbar.update(len(data))

        iso.close()

        # Extract IMS part
        with open(game_iso, "rb") as f, open(extract_to / "_header.ims", "wb+") as g:
            f.seek(0)
            g.write(f.read(273 * 0x800))
            f.seek(-0x800, 2)
            g.write(f.read(0x800))
    

    def make_iso(self) -> None:  

        print("Creating new iso...")

        # We now pack the iso using every shortcut imaginable
        # because realistically we won't really touch anything 
        # apart from the DAT.BIN and SLPS files
        # The logic was basically taken from PS2 Iso Rebuilder

        # Let's clean old build (if they exists)
        self.clean_builds(self.paths["game_builds"])

        # Set up new iso name
        n: datetime.datetime = datetime.datetime.now()
        new_iso = self.paths["game_builds"] 
        new_iso /= f"TalesOfRebirth_{n.year:02d}{n.month:02d}{n.day:02d}{n.hour:02d}{n.minute:02d}.iso"
        
        with FileIO(new_iso, "wb+") as new:

            # 1st place the logo + iso data from the .ims file
            with open(self.paths["original_files"] / "_header.ims", "rb") as f:
                for _ in tqdm(range(273), desc="Copying iso header"):
                    new.write(f.read(0x800))
                anchor_save = f.read(0x800)


            # place the file data in
            files = [
                self.paths["original_files"] / "SYSTEM.CNF",
                self.paths["temp_files"] / "SLPS_254.50",
                self.paths["original_files"] / "IOPRP300.IMG",
                self.paths["original_files"] / "BOOT.IRX",
                self.paths["original_files"] / "MOV.BIN",
            ]

            for file in files:
                with open(file, "rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(0)
                    with tqdm(total=size, desc=f"Inserting {file.name}", unit="B", unit_divisor=1024, unit_scale=True) as pbar:
                        while data := f.read(0x10000000):
                            new.write(data)
                            pbar.update(len(data))
                new.write_padding(0x800)

            
            # Now we plop the new DAT.BIN in its legitimate spot
            sectors: list[int] = [0]
            remainders: list[int] = []
            total = (self.POINTERS_END - self.POINTERS_BEGIN) // 4
            dat_sz = 0
            with tqdm(total=total-1, desc="Inserting DAT.BIN") as pbar:
                for blob, skip in self._pack_dat_iter(sectors, remainders):
                    new.write(blob)
                    dat_sz += len(blob)
                    pbar.update(skip)
                remainders.append(0)
            
            # Align to nearest LBA
            new.write_padding(0x800)
            # get FIELD.BIN LBA
            fld_lba = new.tell() // 0x800

            # Now we plop FIELD.BIN in its legitimate spot
            with open(self.paths["original_files"] / "FLD.BIN", "rb") as dt:
                dt.seek(0, 2)
                fld_sz = dt.tell()
                dt.seek(0)
                with tqdm(total=fld_sz, desc="Inserting FLD.BIN", unit="B", unit_divisor=1024, unit_scale=True) as pbar:
                    while data := dt.read(0x1000000):
                        new.write(data)
                        pbar.update(len(data))
            
            # Align file and add the 20MiB pad cdvdgen adds
            new.write_padding(0x8000)
            new.write(b"\x00" * 0x13F_F800)

            # get end of volume spot
            end = new.tell()
            end_lba = end // 0x800

            # Put the Anchor in place
            new.write(anchor_save)

            # Now we update the file entries, DAT.BIN only need updated
            # size, FLD.BIN size and LBA, also update the PVD size
            new.write_int32_at(0x82992, dat_sz)
            new.write_int32_at(0x829C2, fld_lba)
            new.write_int32_at(0x8050, end_lba + 1)
            new.write_int32_at(end + 0xC, end_lba + 1)
            new.set_endian("big")
            new.write_int32_at(0x82996, dat_sz)
            new.write_int32_at(0x829C6, fld_lba)
            new.write_int32_at(0x8054, end_lba + 1)
            new.set_endian("little")

            # Finally, the SLPS, it's at the same location and size
            # so no problems for us
            new.seek((274 * 0x800) + self.POINTERS_BEGIN)
            for sector, remainder in zip(tqdm(sectors, desc="Updating SLPS offsets"), remainders):
                new.write(struct.pack("<I", sector + remainder))


    def clean_folder(self, path: Path) -> None:
        target_files = list(path.iterdir())
        if len(target_files) != 0:
            print("Cleaning folder...")
            for file in target_files:
                if file.is_dir():
                    shutil.rmtree(file)
                elif file.name.lower() != ".gitignore":
                    file.unlink(missing_ok=False)


    def clean_builds(self, path: Path) -> None:
        target_files = sorted(list(path.glob("*.iso")), key=lambda x: x.name)[:-4]
        if len(target_files) != 0:
            print("Cleaning builds folder...")
            for file in target_files:
                print(f"deleting {str(file.name)}...")
                file.unlink()