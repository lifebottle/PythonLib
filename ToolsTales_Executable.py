import ToolsTOR
import json
import argparse
import textwrap
import os
import io
import re
import requests
import subprocess
import ApacheAutomate
import RepoFunctions
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive


SCRIPT_VERSION = "0.3"
GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = "../client_secrets.json"

def generate_xdelta_patch(repo_name, xdelta_name="Tales-Of-Rebirth_Patch_New.xdelta"):
    
    print("Create xdelta patch")
    original_path = "../Data/{}/Disc/Original/{}.iso".format(repo_name, repo_name)
    new_path = "../Data/{}/Disc/New/{}.iso".format(repo_name, repo_name)
    subprocess.run(["xdelta", "-s", original_path, new_path, xdelta_name])
   
def get_folder(drive, folder_name):

    parent_id = '1xbDBJLg4sVxbvcNFCRC-lA_YXghyKdx8'
    list_folder = drive.ListFile({"q": "'{}' in parents and trashed=false".format(parent_id)}).GetList()
    folder_id=''
    
 
    folder_found = [ele['id'] for ele in list_folder if ele['title'] == folder_name]
    if len(folder_found)>0:
        folder_id = folder_found[0]
        
    else:

     
        file_metadata = {
          'title': folder_name,
          'mimeType': 'application/vnd.google-apps.folder'
        }
        file_metadata['parents'] = [{"kind": "drive#parentReference", "id": parent_id}]
        folder = drive.CreateFile(file_metadata)

        folder.Upload()
        folder_id = folder['id']
        
    return folder_id

def upload_xdelta(xdelta_name, folder_name):
    
    gauth = GoogleAuth()           
    drive = GoogleDrive(gauth)  
    
    xdelta_name = r"G:\TalesHacking\PythonLib_Playground\Data\Tales-Of-Rebirth\Disc\New\Tales-Of-Rebirth_patch.xdelta"
    
    folder_id = get_folder(drive, folder_name)
    
    gfile = drive.CreateFile({'parents': [{'id': folder_id}]})
    
    
    file_name = os.path.basename(xdelta_name)
    gfile['title'] = file_name
    
    gfile.SetContentFile(xdelta_name)
    gfile.Upload() # Upload the file.
    
def get_directory_path(path):
    return os.path.dirname(os.path.abspath(path))

def check_arguments(parser, args):
    if hasattr(args, "elf_path") and not args.elf_path:
        args.elf_path = get_directory_path(args.input) + "/SLPS_254.50"
    
    if hasattr(args, "elf_out") and not args.elf_out:
        args.elf_out = get_directory_path(args.input) + "/NEW_SLPS_254.50"

    if not args.output:
        if not os.path.isdir(args.input):
            args.output = get_directory_path(args.input)
            args.output += "/" + args.input.split("/")[-1]
        else:
            args.output = args.input

def get_arguments(argv=None):
    # Init argument parser
    parser = argparse.ArgumentParser()

    # Add arguments, obviously
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + SCRIPT_VERSION
    )

    parser.add_argument(
         "--game",
        required=True,
        metavar="game_name",
        help="Options: TOR, TOPX, TOH",
        
    )
    sp = parser.add_subparsers(title="Available actions", required=True, dest="action")
    
  
    
    
    # Utility commands
    sp_utility = sp.add_parser(
        "utility",
        description="Usefull functions to be called from Translation App",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    
   
    
    sp_utility.add_argument(
        "function",
        choices=["hex2bytes", "dumptext"],
        metavar="function_name",
        help="Options: hex2bytes, dumptext",
    )
    
    sp_utility.add_argument(
        "param1",
        metavar="param1",
        help="First parameter of a function",
    )
    
    sp_utility.add_argument(
        "param2",
        metavar="param2",
        help="Second parameter of a function",
    )
    
    
    # Unpack commands
    sp_unpack = sp.add_parser(
        "unpack",
        description="Unpacks some file types into more useful ones.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sp_unpack.add_argument(
        "file",
        choices=["All", "Main", "Menu", "Story", "Skits"],
        metavar="FILE",
        help="Options: all, dat, mfh, theirsce, scpk",
    )

    # PAK commands
    sp_pack = sp.add_parser("pack", help="Packs some file types into the originals.")
    
    
    sp_pack.add_argument(
        "file",
        choices=["All", "Main", "Menu","SLPS", "Story", "Skits"],
        metavar="FILE",
        help="Inserts files back into their containers.",
    )

    sp_pack.add_argument(
        "--input",
        metavar="input_path",
        default="DAT.BIN",
        help="Specify custom DAT.BIN output file path.",
        type=os.path.abspath,
    )

    sp_pack.add_argument(
        "--output",
        metavar="output_path",
        default="DAT",
        help="Specify custom dat folder path.",
        type=os.path.abspath,
    )

    sp_pack.add_argument(
        "--elf",
        metavar="elf_path",
        default="../Data/TOR/Disc/Original/SLPS_254.50",
        help="Specify custom SLPS_254.50 (a.k.a ELF) file path.",
        type=os.path.abspath,
    )

    sp_pack.add_argument(
        "--elf-out",
        metavar="elf_output_path",
        default="../Data/TOR/Disc/New/SLPS_254.50",
        help="Specify custom SLPS_254.50 (a.k.a ELF) output file path.",
        type=os.path.abspath,
    )

    # Export commands
    sp_export = sp.add_parser("export", help="Exports, I guess.")
    sp_export.add_argument(
        "file", choices=["table"], metavar="file type", help="Exports data."
    )

    args = parser.parse_args()
    #check_arguments(parser, args)

    return args

def hex2bytes(tales_instance, hex_value):
    
    bytes_value =  bytes.fromhex(hex_value + " 00")
    #print(bytes_value)
    f = io.BytesIO(bytes_value)
    f.seek(0)
    txt, offset = tales_instance.bytesToText(f, -1, b'')
    txt = "\n\n".join([ele for ele in txt.split("{00}") if ele != ""])
    with open("text_dump.txt",  "w",encoding="utf-8") as f:
        f.write(txt)

def getTalesInstance(game_name):
    
    talesInstance = ToolsTOR.ToolsTOR("TBL_All.json")
    #if game_name == "TOR":
    #    talesInstance = ToolsTOR.ToolsTOR("tbl")

    return talesInstance


if __name__ == "__main__":
 
        
    args = get_arguments()
    #print(vars(args))
    
    game_name = args.game
    tales_instance = getTalesInstance(game_name)
    
    #Utility function
    if args.action == "utility":
        
        if args.function == "hex2bytes":
            
            hex2bytes(tales_instance, args.param1)
           
        if args.function == "dumptext":
            
            tales_instance.bytes_to_text_with_offset( args.param1, int(args.param2))
    if args.action == "pack":
        
        RepoFunctions.refresh_repo("PythonLib")
        RepoFunctions.refresh_repo("Tales-Of-Rebirth")
        
        if args.file == "SLPS":
            
            #SLPS
            tales_instance.pack_Menu_File("../Data/Tales-Of-Rebirth/Disc/Original/SLPS_254.50")
            
            ApacheAutomate.apache_job(['SLPS_254.50'], "Tales-Of-Rebirth")
            
            generate_xdelta_patch("Tales-Of-Rebirth", "../Data/Tales-Of-Rebirth/Disc/New/Tales-Of-Rebirth_patch.xdelta")
    if args.action == "unpack":
        
        if args.file == "Main":
            tales_instance.extract_Main_Archive()
            
        if args.file == "Menu":
            print("Extracting Menu Files")
            tales_instance.extract_All_Menu()
            
        if args.file == "Story":
            tales_instance.extract_All_Story_Files()
            
        
                
                