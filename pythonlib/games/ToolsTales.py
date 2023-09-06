import json
import os
import re
import shutil
import string
import struct
import subprocess
from typing import Union
import xml.etree.ElementTree as ET
from pathlib import Path

import lxml.etree as etree
import lxml.etree as ET
import pandas as pd
import pycdlib
import pygsheets
from googleapiclient.errors import HttpError
from tqdm import tqdm
from pythonlib.formats.FileIO import FileIO

import pythonlib.formats.fps4 as fps4
from pythonlib.formats.pak import Pak


class ToolsTales:
    
    COMMON_TAG = r"(<[\w/]+:?\w+>)"
    HEX_TAG    = r"(\{[0-9A-F]{2}\})"
    PRINTABLE_CHARS = "".join(
            (string.digits, string.ascii_letters, string.punctuation, " ")
        )
    VALID_FILE_NAME = r"([0-9]{2,5})(?:\.)?([1,3])?\.(\w+)$"
    VALID_VOICEID = ['VSM_', 'voice_', 'VCT_']

    MAGIC_CHECK = {
        b"SCPK": "scpk",
        b"TIM2": "tm2",
        b"\x7FELF": "irx",
        b"MFH\x00": "mfh",
        b"EBG\x00": "ebg",
        b"anp3": "anp3",
        b"MSCF": "cab",
        b"MGLK": "mglk",
        b"iSE2": "se2",
        b"isdt": "sdt",
        b"iTPK": "tpk",
        b"iTMD": "tmd",
        b"iTDT": "tdt",
        b"XGG\x00": "xgg",
        b"ORG\x00": "org",
        b"fps4": "fps4",
        b"EFFE": "effe",
        b"THEI": "theirsce",
        b"TOD1": "tod1rsce",
        # jr ra :: nop
        b"\x08\x00\xe0\x03": "ovl",
        # lui a2,0x2e :: XX XX 03 24  li v1,XXXX
        b"\x2E\x00\x06\x3C": "ovl",
        b"\x2C\x00\x03\x3C": "ovl",
        b"\xFF\x00\xC6\x30": "ovl",
        b"\x2F\x00\x06\x3C": "ovl",
    }
    
    def __init__(self, gameName, tblFile, repo_name):
        self.jsonTblTags = {}
        self.ijsonTblTags = {}
        self.gameName = gameName
        self.repo_name = repo_name
        self.basePath = os.getcwd()
        self.tblFile = tblFile
        
        
        
        menu_path = "../{}/Data/{}/Menu/MenuFiles.json".format(repo_name, gameName)  
        if os.path.exists(menu_path):
            with open(menu_path) as f:
                self.menu_files_json = json.load(f)
    
        self.make_dirs()
        
    def make_dirs(self):
        self.mkdir('../Data')
        self.mkdir('../Data/{}'.format(self.repo_name))
        self.mkdir('../Data/{}/Disc'.format(self.repo_name))
        self.mkdir('../Data/{}/Disc/Original'.format(self.repo_name))
        self.mkdir('../Data/{}/Disc/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Misc'.format(self.repo_name))
        self.mkdir('../Data/{}/Story'.format(self.repo_name))
        self.mkdir('../Data/{}/Story/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Story/XML'.format(self.repo_name))
        self.mkdir('../Data/{}/Menu'.format(self.repo_name))
        self.mkdir('../Data/{}/Menu/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Menu/XML'.format(self.repo_name))
        self.mkdir('../Data/{}/Skits'.format(self.repo_name))
        self.mkdir('../Data/{}/Skits/New'.format(self.repo_name))
        self.mkdir('../Data/{}/Skits/XML'.format(self.repo_name))
		
    def generate_xdelta_patch(self, xdelta_name):
        
        
        print("Create xdelta patch")
        original_path = "../Data/{}/Disc/Original/{}.iso".format(self.repo_name, self.repo_name)
        new_path = "../Data/{}/Disc/New/{}.iso".format(self.repo_name, self.repo_name)
        subprocess.run(["xdelta", "-f", "-s", original_path, new_path, xdelta_name])
           
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
    def pakComposer_Comptoe(self, file_name, action, file_type, do_comptoe, working):
          
        #Delete the file if already there   
        file_number = file_name.split(".")[0]
        if (action == '-c'):
            if os.path.exists(file_name):
                os.remove( file_name.replace(".pak{}", file_type[1]))
        else:
            
            if os.path.exists(working+"/"+file_number):
                shutil.rmtree(working+"/"+file_number)  
            
        #Run Pakcomposer with parameters
        args = [ "pakcomposer", action, file_name, file_type, "-x"]

        listFile = subprocess.run(
            args,
            cwd=working,
            stdout=subprocess.DEVNULL
            )
        
        if do_comptoe:
            
            files = [ele for ele in os.listdir(working+"/"+file_number) if ".compress" in ele]
            for ele in files:
                
                ctype=0
                with open(working+"/{}/".format(file_number)+ele, "rb") as f:
                    ctype = ord(f.read(1))
            
                args = ["comptoe", "-d{}".format(ctype), ele, ele.split(".")[0]+"d.unknown"]
                listFile = subprocess.run(
                args,
                cwd=working+"/"+file_number,
                stdout=subprocess.DEVNULL
                )
            
            
    def fps4_action(self, action, b_file, destination):
        
        if action == "-d":
            dat_files = [destination + '/' + ele for ele in os.listdir(os.path.dirname(b_file)) if '.dat' in ele]

            if len(dat_files) > 0:
                fps4.dump_fps4(b_file, dat_files[0], destination)
                
        if action == "-c":
            fps4.pack_folder(b_file)
        
        
    def comptoe(self, fileName, action):
          
                
        #Run Pakcomposer with parameters
        args = [ "comptoe", action, fileName, fileName+".res"]
        listFile = subprocess.run(
            args
            )
        
        with open(fileName+".res", "rb") as f:
            data = f.read()
            return data
    
    def decode(self, data):
        if not data[0]:
            return data
        # Be lasy and just assemble bytes.
        sz = (data[2] << 8) | data[1]
        d = iter(data[3:])
        c = 1
        out = bytearray()
        while len(out) < sz:
            if c == 1:
                # Refill.
                c = 0x10000 | next(d) | (next(d) << 8)
            if c & 1:
                p = next(d) | (next(d) << 8)
                l = (p >> 11) + 3
                p &= 0x7FF
                p += 1
                for i in range(l):
                    out.append(out[-p])
            else:
                out.append(next(d))
            c >>= 1
        return bytes(out)

    def _search(self, data, pos, sz):
        ml = min(0x22, sz - pos)
        if ml < 3:
            return 0, 0
        mp = max(0, pos - 0x800)
        hitp, hitl = 0, 3
        if mp < pos:
            hl = data[mp:pos+hitl].find(data[pos:pos+hitl])
            while hl < (pos - mp):
                while (hitl < ml) and (data[pos + hitl] == data[mp + hl + hitl]):
                    hitl += 1
                mp += hl
                hitp = mp
                if hitl == ml:
                    return hitp, hitl
                mp += 1
                hitl += 1
                if mp >= pos:
                    break
                hl = data[mp:pos+hitl].find(data[pos:pos+hitl])
        # If length less than 4, return miss.
        if hitl < 4:
            hitl = 1
        return hitp, hitl-1

    def encode(self, data):
        """"""
        from struct import Struct
        HW = Struct("<H")
    
        cap = 0x22
        sz = len(data)
        out = bytearray(b'\x01')
        out.extend(HW.pack(sz))
        c, cmds = 0, 3
        pos, flag = 0, 1
        out.append(0)
        out.append(0)
        while pos < sz:
            hitp, hitl = self._search(data, pos, sz)
            if hitl < 3:
                # Push a raw if copying isn't possible.
                out.append(data[pos])
                pos += 1
            else:
                tstp, tstl = self._search(data, pos+1, sz)
                if (hitl + 1) < tstl:
                    out.append(data[pos])
                    pos += 1
                    flag <<= 1
                    if flag & 0x10000:
                        HW.pack_into(out, cmds, c)
                        c, flag = 0, 1
                        cmds = len(out)
                        out.append(0)
                        out.append(0)
                    hitl = tstl
                    hitp = tstp
                c |= flag
                e = pos - hitp - 1
                pos += hitl
                hitl -= 3
                e |= hitl << 11
                out.extend(HW.pack(e))
            # Advance the flag and refill if required.
            flag <<= 1
            if flag & 0x10000:
                HW.pack_into(out, cmds, c)
                c, flag = 0, 1
                cmds = len(out)
                out.append(0)
                out.append(0)
        # If no cmds in final word, del it.
        if flag == 1:
            del out[-2:]
        else:
            HW.pack_into(out, cmds, c)
        return bytes(out)
    
    def extract_Story_Pointers(self, theirsce, strings_offset, fsize, bytecode):
        
        
        pointers_offset = []
        texts_offset = []
        
        previous_addr = 0
        while theirsce.tell() < strings_offset:
            b = theirsce.read(1)
            if b == bytecode:
                addr = struct.unpack("<H", theirsce.read(2))[0]
                
                current_pos = theirsce.tell()
                theirsce.seek( addr + strings_offset-1)
                bValidation = theirsce.read(1)
                theirsce.seek(current_pos)
                
                if (addr < fsize - strings_offset) and (addr > 0) and (bValidation == b'\x00'):
                    
                    pointers_offset.append(theirsce.tell() - 2)
                    texts_offset.append(addr + strings_offset)
                    previous_addr = addr
                    
        return pointers_offset, texts_offset
    
    def get_extension(self, data) -> str:
        if data[:4] in self.MAGIC_CHECK:
            return self.MAGIC_CHECK[data[:4]]
        
        if data[:8] == b"IECSsreV":
            if data[0x50:0x58] == b"IECSigaV":
                return "hd"
            elif data[0x30:0x38] == b"IECSidiM":
                return "sq"
            
        if data[:6] == b"D1RXGM":
            return "xgm"
        
        if data[:6] == b"D1RXGS":
            return "xgs"
    
        if data[:16] == b"\x00" * 0x10:
            if data[16:18] != b"\x00\x00":
                return "bd"
            
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
    
    def get_pak_type(self,data) -> Union[str, None]:
        is_aligned = False
        
        data_size = len(data)
        if data_size < 0x8:
            return None
    
        files = struct.unpack("<I", data[:4])[0]
        first_entry = struct.unpack("<I", data[4:8])[0]
    
        # Expectations
        pak1_header_size = 4 + (files * 8)
        pakN_header_size = 4 + (files * 4)
    
        # Check for alignment
        if first_entry % 0x10 == 0:
            is_aligned = True
        
        if pak1_header_size % 0x10 != 0:
            pak1_check = pak1_header_size + (0x10 - (pak1_header_size % 0x10))
        else:
            pak1_check = pak1_header_size
        
        if pakN_header_size % 0x10 != 0:
            pakN_check = pakN_header_size + (0x10 - (pakN_header_size % 0x10))
        else:
            pakN_check = pakN_header_size
    
        # First test pak0 (hope there are no aligned pak0 files...)
        if len(data) > pakN_header_size:
            calculated_size = 0
            for i in range(4, (files + 1) * 4, 4):
                calculated_size += struct.unpack("<I", data[i : i + 4])[0]
            if calculated_size == len(data) - pakN_header_size:
                return "pak0"
    
        # Test for pak1
        if is_aligned:
            if pak1_check == first_entry:
                return "pak1"
        elif pak1_header_size == first_entry:
                return "pak1"
    
        # Test for pak2
        offset = struct.unpack("<I", data[0:4])[0]
    
        if data[offset:offset+8] == b"THEIRSCE":
            return "pak2"
        elif data[offset:offset+8] == b"IECSsreV":
            return "apak"
        
        #Test for pak3
        previous = 0
        for i in range(files):
            file_offset = struct.unpack("<I", data[4*i+4: 4*i+8])[0]

            if file_offset > previous and file_offset >= pakN_header_size:
                previous = file_offset
            else:
                break
            
            if data[4*i+8: first_entry] == b'\x00' * (first_entry - (4*i+8)):
                return "pak3"
    
        # Didn't match anything
        return None


    def extract_Cab(self, cab_file_name, new_file_name, working_dir):
        
        folder_name = os.path.basename(new_file_name).split('.')[0].lower()
        self.mkdir( working_dir + "/" + folder_name)
        #os.mkdir("{}/{}".format(working_dir,folder_name))
        subprocess.run(['expand', os.path.basename(cab_file_name), folder_name + '/{}.dat'.format(folder_name)], cwd=working_dir, stdout=subprocess.DEVNULL)
      
    def make_Cab(self, dat_file_name, cab_file_name, working_dir):
        
        subprocess.run(['makecab', '/D', 'CompressionType=LZX', '/D', 'CompressionMemory=15', '/D', 'ReservePerCabinetSize=8', dat_file_name, cab_file_name ], cwd=working_dir)
    def get_file_name(self, path):
        return os.path.splitext(os.path.basename(path))[0]

    def bytes_to_text_with_offset(self, file_name, start_offset, end_strings):
        
        #Open file
        f = open(file_name, "rb")
        fsize = os.path.getsize(file_name)
        f.seek(start_offset)

        
        root = etree.Element('Text')
        val = b'02'
        while( f.tell() < fsize ):
            
            pos = f.tell()
            if (val != b'\x00'):
                
                
                offset = hex(pos).replace("0x","")
                text, hex_values = self.bytes_to_text(f)
                node = etree.SubElement( root, "Entry")
                etree.SubElement(node, "TextOffset").text = offset
                etree.SubElement(node, "HexValues").text = hex_values
                etree.SubElement(node, "Japanese").text = text
                
                
                val = f.read(1)
                f.seek( f.tell()-1) 

            else:
                val = f.read(1)
                if (val != b'\x00'):
                    f.seek( f.tell()-1)
             
        
        
        f.close()
        
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
        with open('test.xml', "wb") as xmlFile:
            xmlFile.write(txt)
        
    def hex2(self, n):
        x = '%x' % (n,)
        return ('0' * (len(x) % 2)) + x
    
    def str2(self, n):
        return ('0' * (len(n) % 2)) + n
    
    
    #Convert text to Bytes object to reinsert text into THEIRSCE and other files
    def text_to_bytes(self, text):
        multi_regex = (self.HEX_TAG + "|" + self.COMMON_TAG + r"|(\n)")
        tokens = [sh for sh in re.split(multi_regex, text) if sh]
        
        output = b''
        for t in tokens:
            # Hex literals
            if re.match(self.HEX_TAG, t):
                output += struct.pack("B", int(t[1:3], 16))
            
            # Tags
            elif re.match(self.COMMON_TAG, t):
                tag, param, *_ = t[1:-1].split(":") + [None]

                if param is not None:
                    output += struct.pack("B", self.ijsonTblTags["TAGS"].get(tag) or int(tag, 16))
                    if "unk" in tag.lower():
                        output += bytes.fromhex(self.str2(param))
                    else:
                        output += struct.pack("<I", int(param, 16))
                else:
                    if tag in self.ijsonTblTags["TAGS"]:
                        output += struct.pack("B", self.ijsonTblTags["TAGS"][tag])
                        continue
                    for k, v in self.ijsonTblTags.items():
                        if tag in v:
                            output += struct.pack("B", self.ijsonTblTags["TAGS"][k.lower()])
                            output += struct.pack("<I", v[tag])
                            break

            # Actual text
            elif t == "\n":
                output += b"\x01"
            else:
                for c in t:
                    if c in self.PRINTABLE_CHARS or c == "\u3000":
                        output += c.encode("cp932")
                    else:
                        output += struct.pack(">H", self.ijsonTblTags["TBL"].get(c, int.from_bytes(c.encode("cp932"), "big")))

        return output
        
    def search_all_files(self, japanese_text):
        
        #Return the bytes for that specific text
        bytes_from_text = self.text_to_bytes(japanese_text)

    def copy_XML_Translations(self, current_XML_path, new_XML_path):
        
        tree = etree.parse(current_XML_path)
        current_root = tree.getroot()
        tree = etree.parse(new_XML_path)
        new_root = tree.getroot()
    
        keys = [ele.find("JapaneseText").text for ele in  current_root.iter("Entry") ]
        items =  [ele for ele in current_root.iter("Entry")]
        dict_current_translations = dict(zip(keys, items))
            
        for new_entry in new_root.iter("Entry"):
            jap_text = new_entry.find("JapaneseText").text or ''

            #Remove voiceId because its part of a node now
            if jap_text.startswith("<voice:"):
                jap_text = re.split(self.COMMON_TAG, jap_text)[2]

            if jap_text in dict_current_translations:
                entry_found = dict_current_translations[jap_text]
                
                if entry_found.find("EnglishText").text != "" and entry_found.find("Status").text != "To Do":
                    new_entry.find("EnglishText").text = entry_found.find("EnglishText").text
                    new_entry.find("Status").text = entry_found.find("Status").text
                    new_entry.find("Notes").text = entry_found.find("Notes").text
            
        txt=etree.tostring(new_root, encoding="UTF-8", pretty_print=True)
        with open(new_XML_path, "wb") as xmlFile:
            xmlFile.write(txt)

    def denkou_Copy_Script(self, source_folder):
        destinationFolder = '../{}/Data/{}/Story/XML'.format(self.repo_name, self.gameName)
        fileList = os.listdir(source_folder)
        dictionnary = {}

        for file in fileList:
            with open(os.path.join(source_folder, file), 'r', encoding='utf-8') as f:
                contents = f.read()
                tree = ET.fromstring(contents)

                for entry in tree.iter("Entry"):
                    key = entry.find("JapaneseText").text
                    value = entry.find("EnglishText").text

                    if key and key not in dictionnary and value:
                        dictionnary[key] = value
                        #print(key + " = " + value)

        fileList = os.listdir(destinationFolder)

        for file in fileList:
            save = False

            with open(os.path.join(destinationFolder, file), 'r', encoding='utf-8') as f:
                contents = f.read()
                tree = ET.fromstring(contents)

                for entry in tree.iter("Entry"):
                    key = entry.find("JapaneseText").text

                    if key in dictionnary:
                        entry.find("EnglishText").text = dictionnary[key]

                        if key == entry.find("EnglishText").text:
                            entry.find("Status").text = "Done"
                        else:
                            entry.find("Status").text = "Editing"
                        save = True

            if save:
                saveTree = ET.ElementTree(tree)
                saveTree.write(os.path.join(destinationFolder, file), pretty_print=True, xml_declaration=False,
                               encoding="utf-8")
    def copy_XML_English_Translations(self, current_XML_path, new_XML_path):
        
        tree = etree.parse(current_XML_path)
        current_root = tree.getroot()
        tree = etree.parse(new_XML_path)
        new_root = tree.getroot()
    
        keys = [ele.find("PointerOffset").text for ele in  current_root.iter("Entry") ]
        items =  [ele for ele in current_root.iter("Entry")]
        dict_current_translations = dict(zip(keys, items))
            
        for new_entry in new_root.iter("Entry"):
            pointer_offset = new_entry.find("PointerOffset").text
            
            if pointer_offset in dict_current_translations:
                entry_found = dict_current_translations[pointer_offset]
                text = entry_found.find("JapaneseText").text or ''
                occ_list = [ele for ele in [*text] if ele in self.PRINTABLE_CHARS]
                if entry_found.find("JapaneseText").text != "" and len(occ_list) > 0:
                    new_entry.find("EnglishText").text = entry_found.find("JapaneseText").text
                    new_entry.find("Status").text = "Editing"
                    new_entry.find("Notes").text = entry_found.find("Notes").text
            
        txt=etree.tostring(new_root, encoding="UTF-8", pretty_print=True)
        with open(new_XML_path, "wb") as xmlFile:
            xmlFile.write(txt)
        
    def create_Entry(self, strings_node, pointer_offset, text, emb = None, max_len = 0):
        
        #Add it to the XML node
        entry_node = etree.SubElement(strings_node, "Entry")
        etree.SubElement(entry_node,"PointerOffset").text = str(pointer_offset).replace(", ",",")

        if emb is not None:
            emb_node = etree.SubElement(entry_node,"EmbedOffset")
            etree.SubElement(emb_node, "hi").text = str(emb[0])[1:-1].replace(", ",",")
            etree.SubElement(emb_node, "lo").text = str(emb[1])[1:-1].replace(", ",",")
        
        if max_len != 0:
            etree.SubElement(entry_node,"MaxLength").text = str(max_len)

        text_split = re.split(self.COMMON_TAG, text)
        
        if len(text_split) > 1 and any(possible_value in text for possible_value in self.VALID_VOICEID):
            etree.SubElement(entry_node,"VoiceId").text  = text_split[1]
            etree.SubElement(entry_node, "JapaneseText").text = ''.join(text_split[2:])
        else:
            etree.SubElement(entry_node, "JapaneseText").text = text
        
        etree.SubElement(entry_node,"EnglishText")
        etree.SubElement(entry_node,"Notes")
        etree.SubElement(entry_node,"Id").text            = str(self.id)
        
        self.id = self.id + 1
        
        if text == '':
            statusText = 'Done'
        else:
            statusText = 'To Do'
        etree.SubElement(entry_node,"Status").text        = statusText
        
        
    def create_Node_XML(self, fileName, list_informations, section, parent):
        
        root = etree.Element(parent)
        strings_node = etree.SubElement(root, 'Strings')
        etree.SubElement(strings_node, 'Section').text = section
        

        for s, pointers_offset, text in list_informations:
            self.create_Entry( strings_node,  pointers_offset, text)
         
        return root
       
    def remove_duplicates(self, section_list, pointers_offset, texts_list):
        
        final_list = []
        unique_text = set(texts_list)
        for text in unique_text:
            
            indexes = [index for index,ele in enumerate(texts_list) if ele == text]


            
            found = [str(pointers_offset[i]) for i in indexes]
            found.sort(reverse=False)
            found = list( set(found))
            pointers_found = ",".join(found)
           
            section = [section_list[i] for i in indexes][0]
            final_list.append( (section, pointers_found, text))
        
        final_list.sort()

        return final_list

    def extract_Google_Sheets(self, googlesheet_id, sheet_name):
        
        creds_path = r"..\gsheet.json"
        
        if os.path.exists(creds_path):      
            
            try:
                gc = pygsheets.authorize(service_file=creds_path)
                sh = gc.open_by_key(googlesheet_id)
                sheets = sh.worksheets()
                id_sheet = [ ele.index for ele in sheets if ele.title == sheet_name ]
                
                if len(id_sheet) > 0:
                    wks = sh[id_sheet[0]]
                    df = pd.DataFrame(wks.get_all_records())
                    
                    if len(df) > 0:
                        return df
                    else:
                        print("Python didn't find any table with rows in this sheet")
                            
                else:
                    print("{} was not found in the googlesheet {}".format(sheet_name, googlesheet_id))
                        
            except HttpError as e:
                print(e)         
        
        else:
            print("{} was not found to authenticate to Googlesheet API".format(creds_path))
            
    

    #############################
    #
    # Insertion of texts and packing of files
    #
    #############################
    def get_node_bytes(self, entry_node):
        status = entry_node.find("Status").text
        japanese_text = entry_node.find("JapaneseText").text
        english_text = entry_node.find("EnglishText").text
        
        #Use the values only for Status = Done and use English if non empty
        final_text = ''
        if (status not in ['Problematic', 'To Do']):
            final_text = english_text or japanese_text or ''
        else:
            final_text = japanese_text or ''

        voiceId_node = entry_node.find("VoiceId")
        if (voiceId_node != None):
            final_text = '<voice:{}>'.format(voiceId_node.text) + final_text

            #print(final_text)
        #Convert the text values to bytes using TBL, TAGS, COLORS, ...
        bytes_entry = self.text_to_bytes(final_text)
        
        return bytes_entry
    
    
    def pack_Menu_File(self, menu_file_path):
        #Load all the banks for insertion and load XML
        new_text_offsets = dict()

        file_node = [ele for ele in self.menu_files_json if ele['File_Extract'] == menu_file_path][0]
        
        xml_file_name = "../{}/Data/{}/Menu/XML/".format(self.repo_name, self.gameName) + self.get_file_name(menu_file_path)+'.xml'
        tree = etree.parse(file_node['File_XML'])
        root = tree.getroot()
        
        sections_start = [ section['Text_Start'] for section in file_node['Sections'] if section['Text_Start'] > 0 ]
        sections_end   = [ section['Text_End'] for section in file_node['Sections'] if section['Text_Start'] > 0 ]
        sections = [ section for section in file_node['Sections'] if section['Text_Start'] > 0 ]
        base_offset = file_node['Base_Offset']
        
        new_file_path = file_node['File_Extract']

        #Open the new file with r+b
        section_id = 0
        with open(new_file_path, "r+b") as menu_file:
        
            
            menu_file.seek( int(sections[section_id]["Text_Start"]) )
            section_max = max( [int(ele['Text_End']) for ele in sections] )
          
            for entry_node in root.iter("Entry"):
                
                if menu_file.tell() < section_max: 
                    #Calculate the number of bytes
                    #Grab the fields from the Entry in the XML
                    status = entry_node.find("Status").text
                    japanese_text = entry_node.find("JapaneseText").text
                    english_text = entry_node.find("EnglishText").text
                    
                    #Use the values only for Status = Done and use English if non empty
                    final_text = ''
                    if (status not in ['Problematic', 'To Do']):
                        final_text = english_text or japanese_text or ''
                    else:
                        final_text = japanese_text or ''
                        
                    #Convert the text values to bytes using TBL, TAGS, COLORS, ...
                    bytesEntry = self.text_to_bytes(final_text)
                    nb_bytes = len(bytesEntry)
                    new_offset = menu_file.tell() + nb_bytes 
                    
                    pos=0
                    if new_offset < int(sections[section_id]['Text_End']):
                        
                        pos = menu_file.tell()
                    else:
                        
                        section_id = section_id+1
                        
                        if (section_id < len( sections )): 
                            print("Going at : {} ({})".format( sections[section_id]['Section'],  hex( int(sections[section_id]['Text_Start']) )))
                            menu_file.seek( int(sections[section_id]['Text_Start']) )
                            pos = menu_file.tell()
                        else:
                            break
                    
           
                    #Add the PointerOffset and TextOffset
                    new_text_offsets[entry_node.find("PointerOffset").text] = pos
        
                    #Write to the file
                    menu_file.write(bytesEntry + b'\x00')
                
            #Update the pointers
            for pointer_offset, text_offset in new_text_offsets.items():
                
                pointers_list = pointer_offset.split(",")
                new_value = text_offset - base_offset


                for pointer in pointers_list:
                    
                    menu_file.seek(int(pointer))
                    menu_file.write( struct.pack("<L", new_value))

    
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
    
    
               
   
    def extract_abcde_text(self, filename, modify_xml = True):
        
        with open(filename, "r", encoding="utf-8") as f:
            lines  = f.readlines()
            
            
        final_list = []
        pointer_offset = 0
        text = ""
        start=0
        end=0
        
        lines = [line for line in lines if "//" not in line]
        for index,line in enumerate(lines):
            
            if "#WRITE" in line or  "#W32" in line:
                pointer_offset = int(re.findall(r"\$(\w+)", line)[0],16)
                
                start = index+1
                
            if "[END]" in line:
                
                end = index
                text = "".join(lines[start:(end+1)])
                text = text.replace("[LINE]","").replace("[END]\n","")
            
            final_list.append([pointer_offset, text])
            
            
            
        xml_file_name = "../Data/TOR/Menu/XML/SLPS_254.xml"
        tree = etree.parse(xml_file_name)
        root = tree.getroot()
        
        for pointer_offset,text in final_list:
        
            ele_found = [element for element in root.iter("Entry") if str(pointer_offset) in element.find("PointerOffset").text]
            
            if len(ele_found) > 0:
                ele_found[0].find("EnglishText").text = text
                ele_found[0].find("Status").text = "Done"
            else:
                print(pointer_offset)
        if modify_xml:
            txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
            with open(xml_file_name, "wb") as xmlFile:
                xmlFile.write(txt)
        return final_list
    
    #start_offset : where the pointers start for the section
    # nb_per_block : number of pointers per block before adding step
    # step : number of bytes before the next block
    def get_special_pointers(self, text_start, text_max, base_offset, start_offset, nb_per_block, step, section,file_path=''):
        

 
        if file_path == '':
            file_path = self.elf_original


        f = open(file_path , "rb")
    
        f.seek(start_offset, 0)
        pointers_offset = []
        pointers_value  = []
        list_test = []


        is_bad_count = 0
        while f.tell() < text_start and is_bad_count <3:
            

            block_pointers_offset = [f.tell()+4*i for i in range(nb_per_block)]
            
            block_pointers_value = struct.unpack(f"<{nb_per_block}L", f.read(4 * nb_per_block))
            list_test.extend(block_pointers_value)
            
            
            for i in range(len(block_pointers_offset)):

                if (block_pointers_value[i] + base_offset >= text_start and block_pointers_value[i] + base_offset < text_max):
                    #print(block_pointers_value[i])
                    pointers_offset.append(block_pointers_offset[i])
                    pointers_value.append(block_pointers_value[i])
                    is_bad_count = 0
      

                else:
                    is_bad_count = is_bad_count = 1
            f.read(step)
        f.close()
        
        #Only grab the good pointers
        good_indexes = [index for index,ele in enumerate(pointers_value) if ele != 0]
        
        pointers_offset = [pointers_offset[i] for i in good_indexes]
        pointers_value = [pointers_value[i] for i in good_indexes]

        return [pointers_offset, pointers_value]
    
    def get_style_pointers(self, text_start, text_max, base_offset, start_offset, style, file_path):
        
        f_size = os.path.getsize(file_path)
        with open(file_path , "rb") as f:
    
            f.seek(start_offset, 0)
            pointers_offset = []
            pointers_value  = []
            split = [ele for ele in re.split(r'(P)|(\d+)', style) if ele]
            ok = True
            
            while ok:
                for step in split:
                    
                    if step == "P":
                        text_offset = struct.unpack("<I", f.read(4))[0]

                        if text_offset < f_size and text_offset >= text_start and text_offset < text_max:
                            pointers_value.append(text_offset)
                            pointers_offset.append(f.tell()-4)
                            
                        else:
                            ok = False
                    else:
                        f.read(int(step))
                        #print(hex(f.tell()))
        
        return pointers_offset, pointers_value
            
   
    def prepare_Menu_File(self, file_original):
        
        file_name = os.path.basename(file_original)
        
        #Copy the files under Menu Folder
        menu_path = "../Data/{}/Menu/New/".format(self.repo_name) 
        shutil.copy( file_original, menu_path+file_name)
        
        #Extract if needed (PakComposer or other)
        if "pak" in file_name:          
            self.pakComposer_Comptoe(file_name, "-d", "-{}".format(file_name[-1]), True, menu_path)
            
        
        
        
    def extract_menu_file(self, file_definition):
        
        
        section_list = []
        pointers_offset_list = []
        texts_list = []

        print(file_definition)
        
        base_offset = int(file_definition['Base_Offset'])
        print("BaseOffset:{}".format(base_offset))
        file_path   = file_definition['File_Extract']
        
        with open(file_path, "rb") as f:

            for section in file_definition['Sections']:
                
                text_start = section['Text_Start']
                text_end = section['Text_End'] 
                  
                #Extract Pointers of the file
                print("Extract Pointers")
                pointers_offset, pointers_value = self.get_style_pointers( text_start, text_end, base_offset, section['Pointer_Offset_Start'], section['Style'], file_path)
                print([hex(pointers_value) for ele in pointers_value])
              
                #Extract Text from the pointers
                print("Extract Text")
                texts = [ self.bytes_to_text(f, ele + base_offset)[0] for ele in pointers_value]
                
                #Make a list
                section_list.extend( [section['Section']] * len(texts)) 
                pointers_offset_list.extend( pointers_offset)
                texts_list.extend( texts )
       
        #Remove duplicates
        list_informations = self.remove_duplicates(section_list, pointers_offset_list, texts_list)

        #Build the XML Structure with the information
        root = self.create_Node_XML(file_path, list_informations, "Menu", "MenuText")
        
        #Write to XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
        with open(file_definition['File_XML'].replace("../{}/Data/{}".format(self.repo_name, self.gameName), "../Data/{}".format(self.repo_name)), "wb") as xmlFile:
            xmlFile.write(txt)
        
        
        
    def extract_all_Menu(self):

        
        print("Extracting Menu Files")
        self.mkdir("../Data/{}/Menu/New".format(self.repo_name))
        
        #Prepare the menu files (Unpack PAK files and use comptoe)
        res = [ self.prepare_Menu_File(ele['File_Original']) for ele in self.menu_files_json]
        
        for file_definition in self.menu_files_json:
           
            print("...{}".format(file_definition['File_Extract']))
            
            self.extract_menu_file(file_definition)
            
    
        
    def extractAllSkits(self):
        print("Extracting Skits")
        
    def extract_main_archive(self):
        print("Main Archive")
        
        
    def unpackGame(self):
        
        self.extractMainArchive()
        
        self.extractAllStory()
    
        self.extractAllSkits()
    
    #Create the final Iso or Folder that will help us run the game translated
    def packGame(self):
        
        #Insert the text translated and repack the files at the correct place
        self.insertAll()

    def extract_Iso(self, umd_iso: Path) -> None:  
    
        print("Extracting ISO files...")
        
        iso = pycdlib.PyCdlib()
        iso.open(str(umd_iso))

        extract_to = Path(f"../Data/{self.repo_name}/Disc/Original/")
        shutil.rmtree(extract_to)

        files = []
        for dirname, _, filelist in iso.walk(iso_path="/"):
            files += [dirname + x for x in filelist]
                
        for file in files:   
            out_path = extract_to / file[1:]   
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            with iso.open_file_from_iso(iso_path=file) as f, open(str(out_path).split(";")[0], "wb+") as output:
                with tqdm(total=f.length(), desc=f"Extracting {file[1:].split(';')[0]}", unit="B", unit_divisor=1024, unit_scale=True, leave=False) as pbar:
                    while data := f.read(2048):
                        output.write(data)
                        pbar.update(len(data))

        iso.close()

        if self.repo_name == "Narikiri-Dungeon-X":
            for element in os.listdir(extract_to):
                if os.path.isdir(os.path.join(extract_to, element)):
                    os.rename(os.path.join(extract_to, element), os.path.join(extract_to, "PSP_GAME"))
                else:
                    os.rename(os.path.join(extract_to, element), os.path.join(extract_to, "UMD_DATA.BIN"))