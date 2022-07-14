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
        
        #super().__init__("TOPX", tbl, "Narikiri-Dungeon-X")
        
        #Load the hash table for the files
        json_file = open('../Data/Narikiri-Dungeon-X/Misc/hashes.json', 'r')
        self.hashes = json.load(json_file)
        json_file.close()
        
        self.repo_name          = 'Narikiri-Dungeon-X'
        self.misc               = '../Data/{}/Misc'.format(self.repo_name)
        self.disc_path          = '../Data/{}/Disc'.format(self.repo_name)
        self.story_XML_extract  = '../Data/{}/Story/'.format(self.repo_name)                       #Files are the result of PAKCOMPOSER + Comptoe here
        self.story_XML_new      = '../{}/Data/NDX/Story/XML/All/'.format(self.repo_name)                 #Files need to be .CAB here
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
        
        #3) Grab TSS file from PAK3 folder
        tss = self.get_tss_from_pak3(  file_name.replace(".pak3", ""))
        
        #4) Extract TSS to XML
    def get_tss_from_pak3(self, pak3_folder):
          
        if os.path.isdir(pak3_folder):
            folder_name = os.path.basename(pak3_folder)
            file_list = [os.path.dirname(pak3_folder) + "/" + folder_name + "/" + ele for ele in os.listdir(pak3_folder)]
         
            for file in file_list:
                with open(file, "rb") as f:
                    data = f.read()
                  
                    if data[0:3] == b'TSS':
                        print("Extract TSS for file {}".format(folder_name))
                        return io.BytesIO(data)
 
    def extract_tss_XML(self, tss, cab_file_name):
        
        root = etree.Element('SceneText')
        
        stringsNode = etree.SubElement(root, "Strings")
                           
        #Start of the pointer
        pointer_block = struct.unpack("<L", tss.read(4))[0]
        
        #Start of the text and baseOffset
        strings_offset = struct.unpack("<L", tss.read(4))[0]
        
        #File size
        fsize = tss.getbuffer().nbytes
        tss.seek(pointer_block, 0)             #Go the the start of the pointer section
        
        
        #Struct
        pointers_offset, texts_offset = self.extract_Story_Pointers(tss, strings_offset, fsize, self.story_string_byte_code)
        
        text_list = [self.bytes_to_text(tss, ele)[0] for ele in texts_offset]
  
   
        #Remove duplicates
        #list_informations = self.remove_duplicates(["Story"] * len(pointers_offset), pointers_offset, text_list)
        
        list_informations = ( ['Story', pointers_offset[i], text_list[i]] for i in range(len(text_list)))
        #Build the XML Structure with the information
        
        
        file_path = self.story_XML_patch +"XML/"+ self.get_file_name(cab_file_name)
        root = self.create_Node_XML(file_path, list_informations, "Story", "SceneText")
    
        
        #Write the XML file
        txt=etree.tostring(root, encoding="UTF-8", pretty_print=True)
    
        with open(os.path.join( self.story_XML_patch,"XML", self.get_file_name(cab_file_name)+".xml"), "wb") as xmlFile:
            xmlFile.write(txt)
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
                
    # Extract the file all.dat to the different directorties
    def extract_Main_Archive(self):
        
      
        order = {}
        order['order'] = []
        order_json = open( os.path.join( self.misc, 'order.json'), 'w')
        
        #Extract decrypted eboot
        self.extract_Decripted_Eboot()
        
        print("Extract All.dat")
        #Open the eboot
        eboot = open( os.path.join( self.misc, 'EBOOT_DEC.BIN'), 'rb')
        eboot.seek(0x1FF624)
        
        while True:
            file_info = struct.unpack('<3I', eboot.read(12))
            if(file_info[2] == 0):
                break
            hash_ = '%08X' % file_info[2]
            self.extract_files(file_info[0], file_info[1], hash_)
            order['order'].append(hash_)
        json.dump(order, order_json, indent = 4)
        order_json.close()
        
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