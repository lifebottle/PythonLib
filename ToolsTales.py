import subprocess
from dicttoxml import dicttoxml
import json
import struct
import shutil
import os
import re
import fps4
import pandas as pd
import xml.etree.ElementTree as ET
import lxml.etree as etree
from xml.dom import minidom
import re
import collections
import comptolib
import lxml.etree as ET
import string

class ToolsTales:
    
    COMMON_TAG = r"(<\w+:?\w+>)"
    HEX_TAG    = r"(\{[0-9A-F]{2}\})"
    PRINTABLE_CHARS = "".join(
            (string.digits, string.ascii_letters, string.punctuation, " ")
        )
    VALID_FILE_NAME = r"([0-9]{2,5})(?:\.)?([1,3])?\.(\w+)$"
    
    def __init__(self, gameName, tblFile, repo_name):
        
        self.gameName = gameName
        self.repo_name = repo_name
        self.basePath = os.getcwd()
        self.tblFile = tblFile
        
        
        
        menu_path = "../{}/Data/{}/Menu/MenuFiles.json".format(repo_name, gameName)  
        if os.path.exists(menu_path):
            with open(menu_path) as f:
                self.menu_files_json = json.load(f)
           
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
            cwd=working
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
                cwd=working+"/"+file_number
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
        
    def get_pointers(self, start_offset):

        f = open(self.elf_original , "rb")
    
        f.seek(start_offset, 0)
        pointers = []
    
        while f.tell() < self.POINTERS_END:
            
            p = struct.unpack("<L", f.read(4))[0]
            pointers.append(p)
    
        f.close()
        return pointers
    
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
        
        if data[:4] == b"MSCF":
            return "cab"
        
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
        
        if data[:4] == b"FPS4":
            return "fps4"
    
        is_pak = self.get_pak_type(data)
        if is_pak != None:
            return is_pak
        
        if len(data) > 0x400:
            size = struct.unpack("<I", data[0x400:0x404])[0]
            if len(data) == size + 0x400:
                return "tmsk"
    
        # Didn't match anything
        return "bin"
    
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
    
        # Test for pak1 & pak3
        if is_aligned:
            if pak1_check == first_entry:
                return "pak1"
            elif pakN_check == first_entry:
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


    def extract_Cab(self, cab_file_name, new_file_name, working_dir):
        
        folder_name = os.path.basename(new_file_name).split('.')[0].lower()
        os.mkdir( os.path.join(working_dir, folder_name.upper()))
        subprocess.run(['expand', os.path.basename(cab_file_name), folder_name + '/{}.dat'.format(folder_name)], cwd=working_dir)
      
    
    
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

    
    
    #Convert text to Bytes object to reinsert text into THEIRSCE and other files
    def text_to_bytes(self, text):
        
        
       
        unames = []
        
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
                            if c in self.inames:
                                bytesFinal += struct.pack("B", 0xB)
                                bytesFinal += struct.pack("<I", self.inames[c])
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
        
    def search_all_files(self, japanese_text):
        
        #Return the bytes for that specific text
        bytes_from_text = self.text_to_bytes(japanese_text)

    def create_Entry(self, strings_node, pointer_offset, text):
        
        #Add it to the XML node
        entry_node = etree.SubElement(strings_node, "Entry")
        etree.SubElement(entry_node,"PointerOffset").text = str(pointer_offset)
        etree.SubElement(entry_node,"JapaneseText").text  = text
        etree.SubElement(entry_node,"EnglishText").text   = ''
        etree.SubElement(entry_node,"Notes").text         = ''
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
        
        creds_path = "..\gsheet.json"
        
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
    
    def pack_Menu_File(self, menu_file_path):
        
        
        #Load all the banks for insertion and load XML
        new_text_offsets = dict()

        file_node = [ele for ele in self.menu_files_json if ele['File_Extract'] == menu_file_path][0]
        
        xml_file_name = "../{}/Data/{}/Menu/XML/".format(self.repo_name, self.gameName) + self.get_file_name(menu_file_path)+'.xml'
        tree = etree.parse(xml_file_name)
        root = tree.getroot()
        
        sections_start = [ section['Text_Start'] for section in file_node['Sections'] if section['Text_Start'] > 0 ]
        sections_end   = [ section['Text_End'] for section in file_node['Sections'] if section['Text_Start'] > 0 ]
        base_offset = file_node['Base_Offset']
        
     
        #Copy the original file 
        new_file_path = "../Data/{}/Menu/New/{}".format(self.repo_name, os.path.basename(file_node['File_Original']))
        shutil.copy( file_node['File_Extract'], new_file_path)
        
        #Open the new file with r+b
        section_id = 0
        with open(new_file_path, "r+b") as menu_file:
        
            
            menu_file.seek(sections_start[section_id])
            section_max = max( sections_end )
            
            ele = [ele for ele in root.findall("Strings") if ele.find('Section').text == "Armor"][0]
          
            for entry_node in root.iter("Entry"):
                
                if menu_file.tell() < section_max: 
                    #Calculate the number of bytes
                    #Grab the fields from the Entry in the XML
                    status = entry_node.find("Status").text
                    japanese_text = entry_node.find("JapaneseText").text
                    english_text = entry_node.find("EnglishText").text
                    
                    print(english_text)
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
                    if new_offset < sections_end[section_id]:
                        
                        pos = menu_file.tell()
                    else:
                        
                        section_id = section_id+1
                        
                        if (section_id < len( sections_start )): 
                            print("Going at : {} ({})".format( sections_start[section_id] ,  hex( sections_start[section_id] )))
                            menu_file.seek( sections_start[section_id] )
                            pos = menu_file.tell()
                        else:
                            break;
                    
           
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
                pointer_offset = int(re.findall("\$(\w+)", line)[0],16)
                
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
   
    def prepare_Menu_File(self, file_original):
        
        file_name = os.path.basename(file_original)
        
        #Copy the files under Menu Folder
        menu_path = "../Data/{}/Menu/New/".format(self.gameName) 
        shutil.copy( file_original, menu_path+file_name)
        
        #Extract if needed (PakComposer or other)
        if "pak" in file_name:          
            self.pakComposer_Comptoe(file_name, "-d", "-{}".format(file_name[-1]), True, menu_path)
            
        
        
        
    def extract_Menu_File(self, file_definition):
        
        
        section_list = []
        pointers_offset_list = []
        texts_list = []

         
        base_offset = file_definition['Base_Offset']
        file_path   = file_definition['File_Extract']
        
        with open(file_path, "rb") as f:

            for section in file_definition['Sections']:
                
        
                text_start = section['Text_Start']
                text_end = section['Text_End'] 
                  
                #Extract Pointers of the file
                print("Extract Pointers")
                pointers_offset, pointers_value = self.get_special_pointers( text_start, text_end, base_offset, section['Pointer_Offset_Start'], section['Nb_Per_Block'], section['Step'], section['Section'], file_path)
   
              
                #Extract Text from the pointers
                print("Extract Text")
                texts = [ self.bytes_to_text(f, ele + base_offset)[0] for ele in pointers_value]
                print(texts)
                
                #Make a list
                section_list.extend( [section['Section']] * len(texts)) 
                pointers_offset_list.extend( pointers_offset)
                texts_list.extend( texts )
       
        #Remove duplicates
        list_informations = self.remove_duplicates(section_list, pointers_offset_list, texts_list)
        
        #Build the XML Structure with the information
        root = self.create_Node_XML(file_path, list_informations, "MenuText")
        
        #Write to XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
        with open(file_definition['File_XML'].replace("/{}".format(self.repo_name),"").replace("/Data","/Data/{}".format(self.repo_name)), "wb") as xmlFile:
            xmlFile.write(txt)
        
        
        
    def extract_All_Menu(self):

        
        print("Extracting Menu Files")
        self.mkdir("../Data/{}/Menu/New".format(self.repo_name))
        
        #Prepare the menu files (Unpack PAK files and use comptoe)
        files_to_prepare = list(dict.fromkeys([ele['File_Original'] for ele in self.menu_files_json]))
        res = [ self.prepare_Menu_File(ele) for ele in files_to_prepare]
        
        for file_definition in self.menu_files_json:
           
            print("...{}".format(file_definition['File_Extract']))
            
            self.extract_Menu_File(file_definition)
            

        
    def extractAllSkits(self):
        print("Extracting Skits")
        
    def extract_Main_Archive(self):
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
        
                     