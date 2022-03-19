
import sys
import os
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

# Import pycdlib itself.
import pycdlib

    

# Create a new PyCdlib object.
iso = pycdlib.PyCdlib()
iso.open("Tales of Rebirth (Japan)_Backup.iso", "rb+")
outiso = BytesIO()

iso.write_fp(outiso)

    
file_path = "../Data/TOR/Disc/New/SLPS_254.50"


with open(file_path, "rb") as f:
    data = f.read()
    iso.modify_file_in_place(BytesIO(data), len(data), '/{};1'.format(os.path.basename(file_path)))


# Write out the ISO to the file called 'new.iso'.  This will fully master the
# ISO, creating a file that can be burned onto a CD.
iso.write('new.iso')

# Close the ISO object.  After this call, the PyCdlib object has forgotten
# everything about the previous ISO, and can be re-used.
iso.close()