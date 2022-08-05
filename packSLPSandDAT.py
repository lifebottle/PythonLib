import ToolsTOR
import shutil

tool = ToolsTOR.ToolsTOR("TBL_All.json")

print("Packing files into SLPS_254.50")
tool.pack_Menu_File("../Data/Tales-Of-Rebirth/Disc/Original/SLPS_254.50")

tool.pack_Main_Archive()
shutil.copy("../Data/Tales-Of-Rebirth/Menu/New/SLPS_254.50", "../Data/Tales-Of-Rebirth/Disc/New/SLPS_254.50")

#Copy Original Iso
print("Copying Rebirth Iso in New Folder")
shutil.copy("C:/Users/Nick/Documents/Data/Tales-Of-Rebirth/Disc/Original/Tales of Rebirth.iso", "../Data/Tales-Of-Rebirth/Disc/New/Tales of Rebirth.iso")