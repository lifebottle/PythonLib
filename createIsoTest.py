
import sys
import os
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

# Import pycdlib itself.
import pycdlib

def get_file_name(path):
    return os.path.basename(path)
    

# Create a new PyCdlib object.
iso = pycdlib.PyCdlib()
iso.open("Tales of Rebirth (Japan) - Copie.iso")
outiso = BytesIO()

iso.write_fp(outiso)
iso.close()
outiso.seek(0)
dataOriginal = outiso.read()



iso = pycdlib.PyCdlib()
outiso.seek(0)
iso.open_fp(outiso)


with open("Tales of Rebirth (Japan) - Copie.iso", "rb") as f:
    dataIso = f.read()




#Grab datBin files
newDatBinPath = "../Data/Disc/New/Dat.bin"
with open(newDatBinPath, "rb") as datbin:
    datbin_data = datbin.read()

    
#Grab SLPS file
newElfPath = "../Data/Disc/New/SLPS_254.50"
with open(newElfPath, "rb") as slps:
    slps_data = slps.read()


with open("Tales of Rebirth (Japan) - Copie.iso", "r+b") as f:
    
    #DAT.bin
    f.seek(0x6775E800)
    f.write(datbin_data)
    
    f.seek(0x89000)
    f.write(slps_data)
    

    
originalFilePath = "../Data/Disc/Original"
listFiles = [os.path.join(originalFilePath, ele) for ele in os.listdir(originalFilePath) if ele not in ['DAT.BIN', 'SLPS_254.50']]

for file in listFiles:
    with open(file, "rb") as f:
        data = f.read()
        iso.add_fp(BytesIO(data), len(data), '/{};1'.format(os.path.basename(file)))


# Write out the ISO to the file called 'new.iso'.  This will fully master the
# ISO, creating a file that can be burned onto a CD.
iso.write('new.iso')

# Close the ISO object.  After this call, the PyCdlib object has forgotten
# everything about the previous ISO, and can be re-used.
iso.close()