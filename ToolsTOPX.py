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
from xml.dom import minidom
from pathlib import Path
class ToolsTOPX(ToolsTales):
    
    def __init__(self, tbl):
        
        super().__init__("TOPX", tbl)
        
        #Load the hash table for the files
        json_file = open('../Data/Misc/hashes.json', 'r')
        self.hashes = json.load(json_file)
        json_file.close()
        
        self.discPath         = '../Data/Disc'
        self.storyPathExtract = '../Data/Archives/Story/'                       #Files are the result of PAKCOMPOSER + Comptoe here
        self.storyPathInsert  = '../Data/Archives/All/map/pack'                 #Files need to be .CAB here
        self.skitPathExtract  = '../Data/'                                      #Files are the result of PAKCOMPOSER + Comptoe here
        self.allPathExtract   = '../Data/Archives/All/'
        self.allPathInsert    = '../Data/Disc/PSP_GAME/USRDIR'                  #File is all.dat
    
    #############################
    #
    # Extraction of files and unpacking
    #
    #############################
    
    # Make the basic directories for extracting all.dat
    def make_dirs(self):
        self.mkdir('../Data/Archives/All')
        self.mkdir('../Data/Archives/All/battle')
        self.mkdir('../Data/Archives/All/battle/character')
        self.mkdir('../Data/Archives/All/battle/charsnd')
        self.mkdir('../Data/Archives/All/battle/data')
        self.mkdir('../Data/Archives/All/battle/effect')
        self.mkdir('../Data/Archives/All/battle/event')
        self.mkdir('../Data/Archives/All/battle/gui')
        self.mkdir('../Data/Archives/All/battle/map')
        self.mkdir('../Data/Archives/All/battle/resident')
        self.mkdir('../Data/Archives/All/battle/tutorial')
        self.mkdir('../Data/Archives/All/chat')
        self.mkdir('../Data/Archives/All/gim')
        self.mkdir('../Data/Archives/All/map')
        self.mkdir('../Data/Archives/All/map/data')
        self.mkdir('../Data/Archives/All/map/pack')
        self.mkdir('../Data/Archives/All/movie')
        self.mkdir('../Data/Archives/All/snd')
        self.mkdir('../Data/Archives/All/snd/init')
        self.mkdir('../Data/Archives/All/snd/se3')
        self.mkdir('../Data/Archives/All/snd/se3/map_mus')
        self.mkdir('../Data/Archives/All/snd/strpck')
        self.mkdir('../Data/Archives/All/sysdata')
    
    # Extract each of the file from the all.dat
    def extract_files(self, start, size, filename):
        if filename in self.hashes.keys():
            filename = self.hashes[filename]
            input_file = open( '../Data/Disc/Original/PSP_GAME/USRDIR/all.dat', 'rb')
            input_file.seek(start, 0)
            data = input_file.read(size)
            output_file = open( os.path.join(self.allPathExtract, filename), 'wb')
            output_file.write(data)
            output_file.close()
            input_file.close()
    
    # Extract the story files
    def extractAllStory(self):
        
        print("Extracting Story")
        path = os.path.join( self.allPathExtract, 'map/pack/')
        storyPath = '../Data/Archives/Story/'
        self.mkdir(storyPath)
        
        for f in os.listdir( path ):
            if os.path.isfile( path+f) and '.cab' in f:
                
                #Unpack the CAB into PAK3 file
                fileName = storyPath+f.replace(".cab", ".pak3")
                subprocess.run(['expand', path+f, fileName])
                
                #Decompress using PAKCOMPOSER + Comptoe
                super().pakComposerAndComptoe(fileName, "-d", "-3")
                
    def extractAllSkits(self):
        
        print("Extracting Skits")
        path = os.path.join( self.allPathExtract, 'chat/')
        skitsPath ='../Data/Archives/Skits/'
        self.mkdir(skitsPath)
        
        for f in os.listdir(path):
            if os.path.isfile(path + f):
                
                #Unpack the CAB into PAK3 file
                fileName = skitsPath + f.replace(".cab", ".pak3")
                subprocess.run(['expand', path + f, fileName])
                
                #Decompress using PAKCOMPOSER + Comptoe
                super().pakComposerAndComptoe(fileName, "-d", "-3")
    
    def extractAllEvents(self):
        
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
                super().pakComposerAndComptoe(fileName, "-d", "-3")
                
    # Extract the file all.dat to the different directorties
    def extractMainArchive(self):
        
        self.make_dirs()
        order = {}
        order['order'] = []
        order_json = open( os.path.join( self.miscPath, 'order.json'), 'w')
        
        #Extract decrypted eboot
        super().extractDecryptedEboot()
        
        print("Extract All.dat")
        #Open the eboot
        eboot = open( os.path.join( self.miscPath, 'EBOOT_DEC.BIN'), 'rb')
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
        
        
        
    def extractDecryptedEboot(self):
        super().extractDecryptedEboot()