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
    dat_archive_extract   = '../Data/Tales-Of-Rebirth/DAT/' 
    
    def __init__(self, tbl):
        
        super().__init__("TOR", tbl, "Tales-of-Rebirth")
        
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
        self.list_status_insertion = ['Done', 'Proofreading']
    
    
        
    
    
    

    
    # Extract the story files
    def extract_All_Story_Files(self,debug=False):
        
        self.mkdir( self.story_XML_patch + "XML")
        listFiles = [self.dat_archive_extract + 'SCPK/' + ele for ele in os.listdir( os.path.join(self.dat_archive_extract, "SCPK"))]
        for scpk_file in listFiles:

            self.extract_TheirSce_XML(scpk_file)
            self.id = 1
        
    def get_theirsce_from_scpk(self, scpk, scpk_file_name, debug=False)->bytes:
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
                c_type = struct.unpack("<b", data[:1])[0]
                
            if data_decompressed[:8] == b"THEIRSCE":
            
                return io.BytesIO(data_decompressed)
    
        return None
    
    #Extract/Transform Lauren translation
    def extract_Lauren_Translation(self):
        
        #Load Lauren's googlesheet data inside a dataframe
        df = self.extract_Google_Sheets("1-XwzS7F0SaLlXwv1KS6RcTEYYORH2DDb1bMRy5VM5oo", "Story")
        
        #1) Make some renaming and transformations
        df = df.rename(columns = {"KEY":"File", "Japanese":"JapaneseText","Lauren's Script":"EnglishText"})
        
        #2) Filter only relevant rows and columns from the googlesheet
        df = df.loc[ (df['EnglishText'] != ""),:]
        df = df[ ['File', 'JapaneseText', 'EnglishText']]
        
        #3) Make some transformations to the JapaneseText so we can better match with XML
        df['File'] = df['File'].apply( lambda x: x.split("_")[0]+".xml")
        df['JapaneseText'] = df['JapaneseText'].apply( lambda x: re.sub(r"(<\w+:?\w+>)", "", x))
        df['JapaneseText'] = df['JapaneseText'].apply( lambda x: re.sub(r"\[\w+\]", "", x))
        
        return df
            
    # Extract THEIRSCE to XML
    def extract_TheirSce_XML(self, scpk_file_name):
     
        #Create the XML file
        root = etree.Element('SceneText')
        etree.SubElement(root, "OriginalName").text = scpk_file_name
        
        stringsNode = etree.SubElement(root, "Strings")
        
        #Open the SCPK file to grab the THEIRSCE file
        with open(scpk_file_name, "rb") as scpk:
            theirsce = self.get_theirsce_from_scpk(scpk,scpk_file_name,True)
            
            #if (scpk_file_name.endswith(".scpk") and debug):
            #    with open("Debug/{}d.theirsce".format( self.get_file_name(scpk_file_name)), "wb") as f:
            #        f.write(theirsce.read())
                    
        theirsce.seek(0)
        #Validate the header
        header = theirsce.read(8)
        if header != b"THEIRSCE":
            raise ValueError("No THEIRSCE header")
        
        #Start of the pointer
        pointer_block = struct.unpack("<L", theirsce.read(4))[0]
        
        #Start of the text and baseOffset
        strings_offset = struct.unpack("<L", theirsce.read(4))[0]
        
        #File size
        fsize = theirsce.getbuffer().nbytes
        theirsce.seek(pointer_block, 0)             #Go the the start of the pointer section
        pointers_offset, texts_offset = self.extract_Story_Pointers(theirsce, strings_offset, fsize, self.story_byte_code)
        
        text_list = [self.bytes_to_text(theirsce, ele)[0] for ele in texts_offset]
  
   
        #Remove duplicates
        #list_informations = self.remove_duplicates(["Story"] * len(pointers_offset), pointers_offset, text_list)
        
        list_informations = ( ['Story', pointers_offset[i], text_list[i]] for i in range(len(text_list)))
        #Build the XML Structure with the information
        
        
        file_path = self.story_XML_patch +"XML/"+ self.get_file_name(scpk_file_name)
        root = self.create_Node_XML(file_path, list_informations, "Story", "SceneText")
    
        
        #Write the XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
    
        with open(os.path.join( self.story_XML_patch,"XML", self.get_file_name(scpk_file_name)+".xml"), "wb") as xmlFile:
            xmlFile.write(txt)
    
    #Convert a bytes object to text using TAGS and TBL in the json file
    def bytes_to_text(self, fileRead, offset=-1, end_strings = b"\x00"):
    
        finalText = ''
        TAGS = self.jsonTblTags['TAGS']
        
        if (offset > 0):
            fileRead.seek(offset, 0)
        
        pos = fileRead.tell()
        b = fileRead.read(1)
        while b != end_strings:
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
                
                while fileRead.read(1) != b"\x80":
                    fileRead.seek(fileRead.tell()-1)
                    mark = fileRead.read(1)
                    hex_value += mark.hex()
                    if mark == "\x38":
                        hex_value += f"{struct.unpack('<H', fileRead.read(2))[0]:04X}"
         
                finalText += '<{}:{}>'.format(tag_name, hex_value)
                
            elif b in (0x18, 0x19):
                tag_name = f"Unk{b:02X}"
                hex_value = ""
 
                while fileRead.read(1) != b"\x80":
                    fileRead.seek(fileRead.tell()-1)
                    hex_value += fileRead.read(1).hex()
         
                finalText += '<{}:{}>'.format(tag_name, hex_value)

            elif b == 0x81:
                next_b = fileRead.read(1)
                if next_b == b"\x40":
                    finalText += "　"
                else:
                    finalText += "{%02X}" % b
                    finalText += "{%02X}" % ord(next_b)
            else:
                finalText += "{%02X}" % b
            b = fileRead.read(1)
       
        end = fileRead.tell()
        size = fileRead.tell() - pos - 1
        fileRead.seek(pos)
        hex_string = fileRead.read(size).hex()
        hex_values = ' '.join(a+b for a,b in zip(hex_string[::2], hex_string[1::2]))
        fileRead.seek(end)
        return finalText, hex_values
    
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
        

        #Convert the text values to bytes using TBL, TAGS, COLORS, ...
        bytes_entry = self.text_to_bytes(final_text)
        
        return bytes_entry   
    
    def get_New_Theirsce(self, theirsce, scpk_file_name):
        
        #To store the new text_offset and pointers to update
        new_text_offsets = dict()
        
        #Grab strings_offset for pointers
        theirsce.read(12)
        strings_offset = struct.unpack("<L", theirsce.read(4))[0]
        
              
        #Read the XML for the corresponding THEIRSCE
        file = self.story_XML_new +"XML/"+ self.get_file_name(scpk_file_name)+'.xml'
        #print("XML : {}".format(self.get_file_name(scpk_file_name)+'.xml'))
        
        tree = etree.parse(file)
        root = tree.getroot()
        
        #Go at the start of the dialog
        #Loop on every Entry and reinsert
        theirsce.seek(strings_offset+1)
        for entry_node in root.iter("Entry"):
            
            #Add the PointerOffset and TextOffset
            new_text_offsets[entry_node.find("PointerOffset").text] = theirsce.tell()
            
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
                        theirsce = self.get_New_Theirsce(io.BytesIO(data_uncompressed), scpk_file_name)
                        
                            
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
    
    # Extract the file DAT.BIn to the different directorties
    def extract_Main_Archive(self):
        
        #Create folder and delete everything isinde
        #shutil.rmtree("../Data/Tales-Of-Rebirth/DAT")
        for file in os.scandir("../Data/Tales-Of-Rebirth/DAT"):
            os.remove(file.path)
        
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
                    print(file)
                    data = self.pack_Story_File(file_name+".scpk")
                      
                else:
                    with open(file, "rb") as f2:
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
        with open("../Data/{}/Menu/New/SLPS_254.50".format(self.repo_name), "r+b") as output_elf:
            output_elf.seek(self.POINTERS_BEGIN)
        
            for i in range(len(sectors) - 1):
                output_elf.write(struct.pack("<L", sectors[i] + remainders[i]))
    
        
    def pack_All_Story_Files(self):
        
        print("Recreating Story files")
        listFiles = [ele for ele in os.listdir( self.story_XML_patch + "New/")]
        for scpk_file in listFiles:
            self.pack_Story_File(scpk_file)
            print("Writing file {} ...".format(scpk_file))
            
    def insert_All(self):
        
        #Updates SCPK based on XMLs data
        
        self.pack_Main_Archive()