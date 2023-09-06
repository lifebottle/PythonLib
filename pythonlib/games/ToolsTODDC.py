import shutil
import struct
from dataclasses import dataclass
from pathlib import Path

import pycdlib
import pyjson5 as json
from tqdm import tqdm

import pythonlib.utils.comptolib as comptolib

from .ToolsTales import ToolsTales


class ToolsTODDC(ToolsTales):
    def __init__(self, project_file: Path) -> None:
        base_path = project_file.parent
        self.jsonTblTags = {}
        self.ijsonTblTags = {}
        with open(project_file, encoding="utf-8") as f:
            jsonRaw = json.load(f)

        self.paths: dict[str, Path] = {
            k: base_path / v for k, v in jsonRaw["paths"].items()
        }

        self.main_exe_name = jsonRaw["main_exe_name"]
        self.asm_file = jsonRaw["asm_file"]

        with open(self.paths["encoding_table"], encoding="utf-8") as f:
            jsonRaw = json.load(f)

        for k, v in jsonRaw.items():
            self.jsonTblTags[k] = {int(k2, 16): v2 for k2, v2 in v.items()}

        for k, v in self.jsonTblTags.items():
            self.ijsonTblTags[k] = {v2: k2 for k2, v2 in v.items()}
        self.id = 1


    def get_datbin_file_data(self) -> list[tuple[int, int]]:
        tbl_path = self.paths["original_files"] / "DAT.TBL"
        with open(tbl_path, "rb") as tbl:
            blob = tbl.read()

        pointers = struct.unpack(f"<{len(blob)//4}I", blob)
        file_data: list[tuple[int, int]] = []
        for c, n in zip(pointers[::2], pointers[2::2]):
            remainder = c & 0x3F
            start = c & 0xFFFFFFC0
            end = (n & 0xFFFFFFC0) - remainder
            file_data.append((start, end - start))

        return file_data


    # Extract the file DAT.BIN to the different directorties
    def extract_main_archive(self) -> None:
        dat_bin_path = self.paths["extracted_files"] / "DAT"
        dat_bin_path.mkdir(exist_ok=True)

        self.clean_folder(dat_bin_path)

        print("Extracting DAT.BIN files...")
        with open(self.paths["original_files"] / "DAT.BIN", "rb") as f:
            for i, (offset, size) in enumerate(tqdm(self.get_datbin_file_data(), desc="Extracting files", unit="file")):

                # Ignore 0 byte files
                if size == 0:
                    continue

                f.seek(offset, 0)
                data = f.read(size)

                if comptolib.is_compressed(data):
                    c_type = struct.unpack("<b", data[:1])[0]
                    data = comptolib.decompress_data(data)
                    extension = self.get_extension(data)
                    fname = f"{i:05d}.{c_type}.{extension}"
                else:
                    extension = self.get_extension(data)
                    fname = f"{i:05d}.{extension}"

                final_path = dat_bin_path / extension.upper()
                final_path.mkdir(exist_ok=True)

                with open(final_path / fname, "wb") as output:
                    output.write(data)


    def extract_Iso(self, game_iso: Path) -> None:

        print("Extracting ISO files...")

        iso = pycdlib.PyCdlib()
        iso.open(str(game_iso))

        extract_to = self.paths["original_files"]
        self.clean_folder(extract_to)

        files = []
        for dirname, _, filelist in iso.walk(iso_path="/"):
            files += [dirname + x for x in filelist]

        for file in files:
            out_path = extract_to / file[1:]
            out_path.parent.mkdir(parents=True, exist_ok=True)

            with iso.open_file_from_iso(iso_path=file) as f, open(
                str(out_path).split(";")[0], "wb+"
            ) as output:
                with tqdm(
                    total=f.length(),
                    desc=f"Extracting {file[1:].split(';')[0]}",
                    unit="B",
                    unit_divisor=1024,
                    unit_scale=True,
                ) as pbar:
                    while data := f.read(0x8000):
                        output.write(data)
                        pbar.update(len(data))

        iso.close()

        # Extract IMS part
        with open(game_iso, "rb") as f, open(extract_to / "_header.ims", "wb+") as g:
            f.seek(0)
            g.write(f.read(274 * 0x800))
            f.seek(-0x800, 2)
            g.write(f.read(0x800))


    def clean_folder(self, path: Path) -> None:
        target_files = list(path.iterdir())
        if len(target_files) != 0:
            print("Cleaning folder...")
            for file in target_files:
                if file.is_dir():
                    shutil.rmtree(file)
                elif file.name.lower() != ".gitignore":
                    file.unlink(missing_ok=False)
