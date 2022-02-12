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
    
    COMMON_TAG = r"(<\w+:?\w+>)"
    HEX_TAG    = r"(\{[0-9A-F]{2}\})"
    POINTERS_BEGIN = 0xD76B0                                            # Offset to DAT.BIN pointer list start in SLPS_254.50 file
    POINTERS_END   = 0xE60C8                                            # Offset to DAT.BIN pointer list end in SLPS_254.50 file
    HIGH_BITS      = 0xFFFFFFC0
    LOW_BITS       = 0x3F
    PRINTABLE_CHARS = "".join(
            (string.digits, string.ascii_letters, string.punctuation, " ")
        )
    VALID_FILE_NAME = r"([0-9]{2,5})(?:\.)?([1,3])?\.(\w+)$"
    
    
    #Path to used
    datBinOriginal   = '../Data/TOR/Disc/Original/DAT.BIN'
    datBinNew        = '../Data/TOR/Disc/New/DAT.BIN'
    elfOriginal      = '../Data/TOR/Disc/Original/SLPS_254.50'
    elfNew           = '../Data/TOR/Disc/New/SLPS_254.50'
    storyPathArchives= '../Data/TOR/Story/SCPK/'                        #Story XML files will be extracted here                      
    storyPathXML     = '../Data/TOR/Story/XML/'                     #SCPK will be repacked here
    skitPathArchives = '../Data/TOR/Skits/'                        #Skits XML files will be extracted here              
    datPathExtract   = '../Data/TOR/DAT/' 
    
    def __init__(self, tbl):
        
        super().__init__("TOR", tbl)
        
        print("Loading TBL json")
        with open("TBL_All.json") as f:
            jsonRaw = json.load(f)
            jsonTblTags = jsonTblTags ={ k1:{ int(k2,16) if (k1 != "TBL") else k2:v2 for k2,v2 in jsonRaw[k1].items()} for k1,v1 in jsonRaw.items()}
            self.jsonTblTags ={ k1:{ int(k2,16) if (k1 != "TBL") else k2:v2 for k2,v2 in jsonRaw[k1].items()} for k1,v1 in jsonRaw.items()}
          
        print("TBL json is loaded")
          
        with open("MenuFiles.json") as f:
            self.menu_files_json = json.load(f)
    
        self.itable = dict([[i, struct.pack(">H", int(j))] for j, i in self.jsonTblTags['TBL'].items()])
        self.itags = dict([[i, j] for j, i in self.jsonTblTags['TAGS'].items()])
        self.inames = dict([[i, j] for j, i in self.jsonTblTags['NAMES'].items()])
        self.icolors = dict([[i, j] for j, i in self.jsonTblTags['COLORS'].items()])
        
        
    
    
    

    
    # Extract the story files
    def extractAllStory(self):
        
        print("Extracting Story")
        self.mkdir( self.storyPathXML)
        listFiles = [self.datPathExtract + 'SCPK/' + ele for ele in os.listdir( os.path.join(self.datPathExtract, "SCPK"))]
        for scpkFile in listFiles:
            self.extractTheirSceXML(scpkFile)
        
    def get_theirsce_from_scpk(self, scpk)->bytes:
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
    
            if self.is_compressed(data):
                data = comptolib.decompress_data(data)
            
            if data[:8] == b"THEIRSCE":
                return io.BytesIO(data)
    
        return None
    
    def extraxtStoryPointers(self, theirsce, strings_offset, fsize):
        
        
        pointers_offset = []
        texts_offset = []
        
        previous_addr = 0
        while theirsce.tell() < strings_offset:
            b = theirsce.read(1)
            if b == b"\xF8":
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
        
    
        
    # Extract THEIRSCE to XML
    def extractTheirSceXML(self, scpkFileName):
     
        #Create the XML file
        root = etree.Element('SceneText')
        etree.SubElement(root, "OriginalName").text = scpkFileName
        
        stringsNode = etree.SubElement(root, "Strings")
        
        #Open the SCPK file to grab the THEIRSCE file
        with open(scpkFileName, "rb") as scpk:
            theirsce = self.get_theirsce_from_scpk(scpk)
            
            if (scpkFileName.endswith(".scpk")):
                with open("Debug/{}.theirsce".format( self.get_file_name(scpkFileName)), "wb") as f:
                    f.write(theirsce.read())
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
        pointers_offset, texts_offset = self.extraxtStoryPointers(theirsce, strings_offset, fsize)
        
        text_list = [self.bytesToText(theirsce, ele)[0] for ele in texts_offset]
  
   
        #Remove duplicates
        list_informations = self.remove_duplicates(["Story"] * len(pointers_offset), pointers_offset, text_list)
        
        #Build the XML Structure with the information
        file_path = self.storyPathXML + self.get_file_name(scpkFileName)
        root = self.create_Node_XML(file_path, list_informations, "SceneText")
    
        #Write the XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
    
        with open(os.path.join( self.storyPathXML, self.get_file_name(scpkFileName)+".xml"), "wb") as xmlFile:
            xmlFile.write(txt)
        
    def getNewTheirsce(self, theirsce, scpkFileName):
        
        #To store the new text_offset and pointers to update
        new_text_offsets = dict()
        
        #Grab strings_offset for pointers
        theirsce.read(12)
        strings_offset = struct.unpack("<L", theirsce.read(4))[0]
        print(strings_offset)
              
        #Read the XML for the corresponding THEIRSCE
        file = self.storyPathXML+ self.get_file_name(scpkFileName)+'.xml'
        print("XML : {}".format(self.get_file_name(scpkFileName)+'.xml'))
        tree = etree.parse(file)
        root = tree.getroot()
        
        theirsce.seek(strings_offset+1)
        for entry_node in root.iter("Entry"):
            
            #Add the PointerOffset and TextOffset
            new_text_offsets[entry_node.find("PointerOffset").text] = theirsce.tell()
            
            #Grab the fields from the Entry in the XML
            status = entry_node.find("Status").text
            japanese_text = entry_node.find("JapaneseText").text
            english_text = entry_node.find("EnglishText").text
            
            #Use the values only for Status = Done and use English if non empty
            final_text = ''
            if (status == "Done"):
                final_text = english_text or japanese_text or ''
            else:
                final_text = japanese_text or ''
            

            #Convert the text values to bytes using TBL, TAGS, COLORS, ...
            bytesEntry = self.textToBytes(final_text)

            #Write to the file
            theirsce.write(bytesEntry + b'\x00')
            
        #Update the pointers
        for pointer_offset, text_offset in new_text_offsets.items():
            
            theirsce.seek(int(pointer_offset))
            theirsce.write( struct.pack("<H", text_offset - strings_offset))
            
        return theirsce
            
    #Repack SCPK files for Story
    def insertStoryFile(self, scpkFileName):
        
        #Copy the original SCPK file to the folder used for the new version
        shutil.copy( self.datPathExtract + "SCPK/" + scpkFileName, self.storyPathArchives + scpkFileName)
        
        #Open the new SCPK file in Read+Write mode
        with open( self.storyPathArchives + scpkFileName, 'r+b') as scpk:
              
            
            #Get nb_files and files_size
            scpk.read(4)
            scpk.read(4)
            nb_files = struct.unpack("<L", scpk.read(4))[0]
            scpk.read(4)
            file_size_dict = dict()
            for i in range(nb_files):
                pointer_offset = scpk.tell()
                file_size_dict[struct.unpack("<L", scpk.read(4))[0]] = pointer_offset
                         
            #Extract each files and append to the final data_final
            dataFinal = b''
            pos = scpk.tell()
            for fsize, pointer_offset in file_size_dict.items():
                
                data = scpk.read(fsize)
                
                data_compressed = data
                if self.is_compressed(data):
                    
                    data_uncompressed = comptolib.decompress_data(data)

                    if data_uncompressed[:8] == b"THEIRSCE":
                        
                        #Only for debug to have  the original THEIRSCE
                        #with open("test_original_comp.theirsce", "wb") as f:
                        #    print("Size original: {}".format(len(data_uncompressed)))
                        #    f.write(data)
                        #with open("test_original.theirsce", "wb") as f:
                        #    f.write(data_uncompressed)
                            
                        #Update THEIRSCE uncompressed file and write to a test file
                        theirsce = self.getNewTheirsce(io.BytesIO(data_uncompressed), scpkFileName)
                        
                        theirsce.seek(0)
                        data_new_uncompressed = theirsce.read()
                        print("Size new: {}".format(len(data_new_uncompressed)))
                        #Only for debug to have  the new THEIRSCE
                        
                        
                        #Compress the new THEIRSCE file
                        c_type = struct.unpack("<b", data[:1])[0]
                        print(c_type)
                        data_compressed = comptolib.compress_data(data_new_uncompressed, version=c_type)
                    
                        #with open("test_new_comp.theirsce", "wb") as f:               
                        #    f.write(data_compressed)
                            
                        #with open("test_new.theirsce", "wb") as f:
                        #    f.write(data_uncompressed)
                            
                        #Updating the header of the SCPK file to adjust the size
                        new_size = len(data_new_uncompressed)
                        if (new_size > len(data_uncompressed)):
                            
                            scpk.seek( pointer_offset)
                            scpk.write( struct.pack("<I", new_size))
                            
                dataFinal += data_compressed
                
            
            scpk.seek(pos)
            scpk.write(dataFinal)
            
    
    # Extract the file DAT.BIn to the different directorties
    def extract_Main_Archive(self):
        
     
        f = open( self.datBinOriginal, "rb")
    
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
            
            
            if self.is_compressed(data):
                c_type = struct.unpack("<b", data[:1])[0]
                data = comptolib.decompress_data(data)
                extension = self.get_extension(data)
                final_path = self.datPathExtract + "/%s/%s.%d.%s" % (
                    extension.upper(),
                    file_name,
                    c_type,
                    extension,
                )
            else:
                extension = self.get_extension(data)
                final_path = self.datPathExtract + "/%s/%s.%s" % (
                    extension.upper(),
                    file_name,
                    extension,
                )
            folderPath = os.path.join( self.datPathExtract, extension.upper())
            self.mkdir( folderPath )
    
            with open(final_path, "wb") as output:
                output.write(data)
            print("Writing file %05d/%05d..." % (i, total_files), end="\r")
    
        print("Writing file %05d/%05d..." % (i, total_files))
        f.close()
        
    def insert_Main_Archive(self):
        sectors = [0]
        remainders = []
        buffer = 0
    
        output_dat_path = self.datBinNew
        output_dat = open(output_dat_path, "wb")
    
        print("Packing files into %s..." % os.path.basename(output_dat_path))
        
        #Make a list with all the files of DAT.bin
        file_list = []
        for path, subdir, filenames in os.walk(r"G:\TalesHacking\PythonLib_Playground\Data\DAT"):
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
    
            comp_type = re.search(self.VALID_FILE_NAME, file).group(2)
            with open(file, "rb") as f2:
                data = f2.read()
                
            if comp_type != None:
                data = comptolib.compress_data(data, version=int(comp_type))
        
            output_dat.write(data)
            size = len(data)
            print("file: {}   size: {}".format(file, size))
            remainder = 0x40 - (size % 0x40)
            if remainder == 0x40:
                remainder = 0
            output_dat.write(b"\x00" * remainder)
          
    
            remainders.append(remainder)
            buffer += size + remainder
            sectors.append(buffer)
            previous += 1
    
            print(
                "Writing file %05d/%05d..." % (current - dummies, len(file_list)), end="\r"
            )
    
        print("Writing file %05d/%05d..." % (current - dummies, len(file_list)))
        
        shutil.copy( self.elfOriginal, self.elfNew)
        output_elf = open(self.elfNew, "r+b")
        output_elf.seek(self.POINTERS_BEGIN)
    
        for i in range(len(sectors) - 1):
            output_elf.write(struct.pack("<L", sectors[i] + remainders[i]))
    
        output_dat.close()
        output_elf.close()