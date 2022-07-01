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

import GoogleAPI

SCRIPT_VERSION = "0.0.3"
def generate_xdelta_patch(repo_name, xdelta_name="Tales-Of-Rebirth_Patch_New.xdelta"):
    
    print("Create xdelta patch")
    original_path = "../Data/{}/Disc/Original/{}.iso".format(repo_name, repo_name)
    new_path = "../Data/{}/Disc/New/{}.iso".format(repo_name, repo_name)
    subprocess.run(["xdelta", "-f", "-s", original_path, new_path, xdelta_name])
   

    
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
    sp = parser.add_subparsers(title="Available actions", required=False, dest="action")
    
  
    
    
    # Utility commands
    sp_utility = sp.add_parser(
        "utility",
        description="Usefull functions to be called from Translation App"
    )
    
   
    
    sp_utility.add_argument(
        "function",
        choices=["hex2bytes", "dumptext"],
        metavar="function_name",
        help="Options: hex2bytes, dumptext",
    )
    
    sp_utility.add_argument(
        "param1",
        help="First parameter of a function",
    )
    
    sp_utility.add_argument(
        "param2",
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

    sp_updateiso = sp.add_parser(
        "updateiso",
        description="Update the iso using Apache",
        formatter_class=argparse.RawTextHelpFormatter,
    )


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

def replace_Files_Apache(files_list, repo):
    
    ApacheAutomate.apache_job(files_list, repo)
    
    
if __name__ == "__main__":
 
        
    args = get_arguments()
    #print(vars(args))
    
    #RepoFunctions.refresh_repo("PythonLib")
    game_name = args.game
    tales_instance = getTalesInstance(game_name)
    
    org = 'SymphoniaLauren'
    repo_name = 'Tales-of-Rebirth'
    RepoFunctions.refresh_repo(repo_name)
    
    #Utility function
    if args.action == "utility":
        
        if args.function == "hex2bytes":
            
            hex2bytes(tales_instance, args.param1)
           
        if args.function == "dumptext":
            
            tales_instance.bytes_to_text_with_offset( args.param1, int(args.param2))
            
            
            
    if args.action == "pack":
        

        
        
        if args.file == "SLPS":
            
            #SLPS
            tales_instance.pack_Menu_File("../Data/Tales-Of-Rebirth/Disc/Original/SLPS_254.50")
            
            
            
            xdelta_name = "../Data/Tales-Of-Rebirth/Disc/New/Tales-Of-Rebirth_patch.xdelta"
            generate_xdelta_patch(repo_name, xdelta_name)
            
            file_link = GoogleAPI.upload_xdelta(xdelta_name, "Stewie")            #Need to add user for the folder
            
            message_text = """
Hi {},

here is your xdelta patch : 
{}
""".format('fortiersteven1@gmail.com', file_link)

            message_text = message_text + "<br>" + RepoFunctions.get_pull_requests_message(org, repo_name)
            GoogleAPI.send_message('fortiersteven1@gmail.com', 'fortiersteven1@gmail.com', game_name + " Patch", file_link, message_text)
            


        if args.file == "Main":
            
            tales_instance.pack_Main_Archive()
            
    if args.action == "updateiso":
        replace_Files_Apache( ['SLPS_254.50', 'DAT.BIN'], repo_name)
    if args.action == "unpack":
        
        if args.file == "Main":
            tales_instance.extract_Main_Archive()
            
        if args.file == "Menu":
            print("Extracting Menu Files")
            tales_instance.extract_All_Menu()
            
        if args.file == "Story":
            tales_instance.extract_All_Story_Files()
            