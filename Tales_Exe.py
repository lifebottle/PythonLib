import argparse
import io
import os
import subprocess

import GoogleAPI
import RepoFunctions
import ToolsNDX
import ToolsTOR

repos_infos ={
    "TOR":
        {
            "Org": "SymphoniaLauren",
            "Repo": "Tales-Of-Rebirth"
        },
    "NDX":
        {
            "Org": "Lifebottle",
            "Repo": "Narikiri-Dungeon-X"
        }
}


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

    parser.add_argument(
        "-g",
        "--game",
        choices=["TOR", "NDX"],
        required=True,
        metavar="game",
        help="Options: TOR, NDX",
    )
    sp = parser.add_subparsers(title="Available actions", required=False, dest="action")

    # # Utility commands
    # sp_utility = sp.add_parser(
    #     "utility",
    #     description="Usefull functions to be called from Translation App"
    # )
    #
    #
    #
    # sp_utility.add_argument(
    #     "function",
    #     choices=["hex2bytes", "dumptext"],
    #     metavar="function_name",
    #     help="Options: hex2bytes, dumptext",
    # )
    #
    # sp_utility.add_argument(
    #     "param1",
    #     help="First parameter of a function",
    # )
    #
    # sp_utility.add_argument(
    #     "param2",
    #     help="Second parameter of a function",
    # )
    # Extract commands
    sp_extract = sp.add_parser(
        "extract",
        description="Extract the content of the files",
        help="Extract the content of the files",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    sp_extract.add_argument(
        "-ft",
        "--file_type",
        choices=["Iso", "Main", "Menu", "Story", "Skits"],
        required=True,
        metavar="file_type",
        help="(Required) - Options: Iso, Init, Main, Menu, Story, Skits",
    )

    sp_extract.add_argument(
        "-i",
        "--iso",
        required=False,
        default="../b-topndxj.iso",
        metavar="iso",
        help="(Optional) - Only for extract Iso command"
    )

    sp_extract.add_argument(
        "-r",
        "--replace",
        required=False,
        metavar="replace",
        default=False,
        help="(Optional) - Boolean to uses translations from the Repo to overwrite the one in the Data folder"
    )

    sp_insert = sp.add_parser(
        "insert",
        help="Take the new texts and recreate the files"
    )

    sp_insert.add_argument(
        "-ft",
        "--file_type",
        choices=["Iso", "Main", "Elf", "Story", "Skits"],
        required=True,
        metavar="file_type",
        help="(Required) - Options: Iso, Init, Main, Elf, Story, Skits",
    )

    # Debug commands
    sp_debug = sp.add_parser(
        "debug",
        description="Used to debug some files",
        help="Used to debug some files",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    sp_debug.add_argument(
        "-ft",
        "--file_type",
        choices=["Menu", "Story", "Skits"],
        metavar="file_type",
        help="Options: Menu, Story, Skits",
    )

    sp_debug.add_argument(
        "-f",
        "--file_name",
        required=False,
        help="File name to debug"
    )

    sp_debug.add_argument(
        "-t",
        "--text",
        required=False,
        help="Boolean to also extract the Japanese text"
    )

    # Export commands
    sp_export = sp.add_parser("export", help="Exports, I guess.")
    sp_export.add_argument(
        "file", choices=["table"], metavar="file type", help="Exports data."
    )

    args = parser.parse_args()
    #check_arguments(parser, args)

    return args


def send_xdelta():
   file_link = GoogleAPI.upload_xdelta(xdelta_name, "Stewie")            #Need to add user for the folder
            
   message_text = """
Hi {},

here is your xdelta patch : 
{}
""".format('fortiersteven1@gmail.com', file_link)

   message_text = message_text + "<br>" + RepoFunctions.get_pull_requests_message(org, repo_name)
   GoogleAPI.send_message('fortiersteven1@gmail.com', 'fortiersteven1@gmail.com', game_name + " Patch", file_link, message_text)
    
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

    if game_name == "TOR":
        talesInstance = ToolsTOR.ToolsTOR("TBL_All.json")
    elif game_name == "NDX":
        talesInstance = ToolsNDX.ToolsNDX("TBL_All.json")
    else:
        raise ValueError("Unkown game name")

    return talesInstance


if __name__ == "__main__":

    args = get_arguments()
    game_name = args.game
    tales_instance = getTalesInstance(game_name)
    org = repos_infos[game_name]["Org"]
    repo_name = repos_infos[game_name]["Repo"]

    if args.action == "insert":

        if args.file_type == "Main":
            tales_instance.pack_Main_Archive()

        elif args.file_type == "Story":
            tales_instance.pack_All_Story()

        elif args.file_type == "Skits":
            tales_instance.pack_All_Skits()

        elif args.file_type == "Elf":
            
            #SLPS
            tales_instance.pack_Menu_File("../Data/Tales-Of-Rebirth/Disc/New/SLPS_254.50")
            
            #Generate Iso
            #xdelta_name = "../Data/Tales-Of-Rebirth/Disc/New/{}.xdelta".format(args.iso.replace(".iso",""))
            #generate_xdelta_patch(repo_name, xdelta_name)

    if args.action == "extract":

        if args.file_type == "Iso":
            tales_instance.extract_Iso(args.iso)
            tales_instance.extract_Main_Archive()

        if args.file_type == "Main":
            tales_instance.extract_Main_Archive()
            
        if args.file_type == "Menu":
            tales_instance.extract_All_Menu()

        if args.file_type == "Story":
            tales_instance.extract_All_Story(args.replace)

        if args.file_type == "Skits":
            tales_instance.extract_All_Skits(args.replace)

    if args.action == "debug":

        if args.file_type in ["Story", "Skits"]:
            tales_instance.debug_Story_Skits(args.file_type, args.file_name, args.text)
