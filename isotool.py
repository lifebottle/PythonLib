import io
import struct
import argparse
from pathlib import Path
from dataclasses import dataclass
import typing

SCRIPT_VERSION = "1.2"
SECTOR_SIZE = 0x800
SYSTEM_AREA_SIZE = 0x10 * SECTOR_SIZE
LAYER0_PVD_LOCATION = SYSTEM_AREA_SIZE


@dataclass
class FileListData:
    path: Path
    inode: int
    lba: int
    size: int = 0


@dataclass
class FileListInfo:
    files: list[FileListData]
    total_inodes: int


def main():
    print(f"pyPS2 ISO Rebuilder v{SCRIPT_VERSION}")
    print("Original by Raynê Games")
    print()

    args = get_arguments()

    if args.mode == "extract":
        dump_iso(args.iso, args.filelist, args.files)
        print("dumping finished")
    else:
        rebuild_iso(args.iso, args.filelist, args.files, args.output, args.with_padding)
        print("rebuild finished")


def get_arguments(argv=None):
    # Init argument parser
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-m",
        "--mode",
        choices=["extract", "insert"],
        required=True,
        metavar="operation",
        help="Options: extract, insert",
    )

    parser.add_argument(
        "--iso",
        required=True,
        type=Path,
        metavar="original_iso",
        help="input game iso file path",
    )

    parser.add_argument(
        "--with-padding",
        required=False,
        action="store_true",
        help="flag to control outermost iso padding",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=False,
        type=Path,
        metavar="output_iso",
        help="resulting iso file name",
    )

    parser.add_argument(
        "--filelist",
        required=False,
        type=Path,
        metavar="filelist_path",
        help="filelist.txt file path",
    )

    parser.add_argument(
        "--files",
        required=False,
        type=Path,
        metavar="files_folder",
        help="path to folder with extracted iso files",
    )

    args = parser.parse_args()
    curr_dir = Path("./").resolve()

    args.iso = args.iso.resolve()
    if hasattr(args, "filelist") and not args.filelist:
        args.filelist = curr_dir / f"{args.iso.name.upper()}-FILELIST-LSN.TXT"

    if hasattr(args, "files") and not args.files:
        args.files = curr_dir / f"@{args.iso.name.upper()}"

    if hasattr(args, "output") and not args.output:
        args.output = curr_dir / f"NEW_{args.iso.name}"

    return args


def check_pvd(fp: typing.BinaryIO, pvd_loc: int) -> bool:
    fp.seek(pvd_loc)
    vd_type, vd_id = struct.unpack("<B5s", fp.read(6))
    if vd_type == 1 and vd_id == b"CD001":
        return True
    else:
        return False


def dump_dir_records(iso: typing.BinaryIO, pvd_loc: int, pvd_off: int) -> FileListInfo:
    path_parts = []
    record_ends = []
    record_pos = []
    file_info = FileListInfo([], 0)

    # get the root directory record off the PVD
    iso.seek(pvd_loc + 0x9E)
    dr_data_pos, dr_data_len = struct.unpack("<I4xI", iso.read(12))
    dr_data_pos *= SECTOR_SIZE
    dr_data_pos += pvd_off
    record_ends.append(dr_data_pos + dr_data_len)
    record_pos.append(0)

    iso.seek(dr_data_pos)

    # Traverse directory records recursively
    # Did I mention that I won't do function recursion?
    while True:
        # Have we reached the end of current dir record?
        if iso.tell() >= record_ends[-1]:
            if len(record_ends) == 1:
                # If it's the last one, we finished
                break
            else:
                # Otherwise keep reading the previous one
                record_ends.pop()
                path_parts.pop()
                iso.seek(record_pos.pop() + pvd_off)
                continue

        # Parse the record
        inode = iso.tell()
        dr_len = struct.unpack("<B", iso.read(1))[0]
        dr_blob = iso.read(dr_len - 1)

        (
            dr_ea_len,
            dr_data_pos,
            dr_data_len,
            dr_flags,
            dr_inter,
            dr_volume,
            dr_name_len,
        ) = struct.unpack_from("<BI4xI4x7xBHH2xB", dr_blob)

        assert dr_ea_len == 0, "ISOs with extra attributes are not supported!"
        assert dr_inter == 0, "Interleaved ISOs are not supported!"
        assert dr_volume == 1, "multi-volume ISOs are not supported!"
        assert (dr_flags & 0b1000000) == 0, "4GiB+ files are not supported!"

        # the dir records always en on even addresses
        if (iso.tell() % 2) != 0:
            iso.read(1)

        dr_data_pos *= 0x800
        dr_data_pos += pvd_off

        dr_name = dr_blob[32 : 32 + dr_name_len]

        # record with these names are the '.' and '..'
        # directories respectively, so skip them
        if dr_name == b"\x00" or dr_name == b"\x01":
            continue

        dr_name = dr_name.decode()
        if dr_name.endswith(";1"):
            dr_name = dr_name[:-2]
        path_parts.append(dr_name)

        file_info.total_inodes += 1

        # is it a directory?
        if (dr_flags & 0b10) != 0:
            # Go to its directory record
            record_pos.append(iso.tell())
            record_ends.append(dr_data_pos + dr_data_len)
            iso.seek(dr_data_pos)
            continue
        else:
            # Otherwise dump the file
            fp = "/".join(path_parts)

            file_info.files.append(
                FileListData(Path(fp), inode, dr_data_pos, dr_data_len)
            )
            path_parts.pop()

    return file_info


def save_iso_files(
    iso: typing.BinaryIO, file_info: FileListInfo, base_folder: Path
) -> None:
    for file in file_info.files:
        print(f"SAVING {file.path.as_posix()}")

        final_path = base_folder / file.path
        final_path.parent.mkdir(exist_ok=True, parents=True)
        iso.seek(file.lba)

        with open(final_path, "wb+") as f:
            f.write(iso.read(file.size))


def dump_iso(iso_path: Path, filelist: Path, iso_files: Path) -> None:
    if iso_path.exists() is False:
        print(f"Could not to find '{iso_path.name}'!")
        return

    with open(iso_path, "rb") as iso:
        # Sanity check
        assert check_pvd(iso, LAYER0_PVD_LOCATION), "No valid PVD found in Layer0!"

        # Test dual-layer-dness
        has_second_layer = False

        iso.seek(LAYER0_PVD_LOCATION + 0x50)
        pvd0_sector_count = struct.unpack("<I", iso.read(4))[0]
        iso.seek(0, io.SEEK_END)
        iso_sector_count = iso.tell() // SECTOR_SIZE
        pvd1_pos = pvd0_sector_count * SECTOR_SIZE

        if iso_sector_count != pvd0_sector_count:
            # sector count of the PVD disagree with the file
            # check for another PVD at volume end
            has_second_layer = check_pvd(iso, pvd1_pos)

            if has_second_layer:
                print("< Dual layer ISO Detected >")
                print()
            else:
                print("WARNING: Iso data suggest this is a double layer image")
                print(
                    "         but no valid PVD was found for Layer1, iso might be corrupt"
                )
                print()

        layer0_data = dump_dir_records(iso, LAYER0_PVD_LOCATION, 0)
        layer0_data.files.sort(
            key=lambda x: x.lba
        )  # The files are ordered based on their disc position

        if has_second_layer:
            layer1_data = dump_dir_records(iso, pvd1_pos, pvd1_pos - SYSTEM_AREA_SIZE)
            layer1_data.files.sort(
                key=lambda x: x.lba
            )  # The files are ordered based on their disc position
        else:
            layer1_data = FileListInfo([], 0)

        # save files
        save_iso_files(iso, layer0_data, iso_files)

        if has_second_layer:
            print("\n< SECOND LAYER >\n")

        save_iso_files(iso, layer1_data, iso_files)

        # Save filelist
        with open(filelist, "w", encoding="utf8") as f:
            if has_second_layer:
                f.write(f"//{len(layer0_data.files)}\n")

            for d in layer0_data.files:
                f.write(f"|{d.inode}||{iso_files.name}/{d.path.as_posix()}|\n")
            f.write(f"//{layer0_data.total_inodes}")

            if has_second_layer:
                f.write("\n")
                for d in layer1_data.files:
                    f.write(f"|{d.inode}||{iso_files.name}/{d.path.as_posix()}|\n")
                f.write(f"//{layer1_data.total_inodes}")


def rebuild_iso(
    iso: Path, filelist: Path, iso_files: Path, output: Path, add_padding: bool
) -> None:
    if filelist.exists() is False:
        print(f"Could not to find the '{filelist.name}' files log!")
        return

    if iso_files.exists() is False:
        print(f"Could not to find the '{iso_files.name}' files directory!")
        return

    if iso_files.is_dir() is False:
        print(f"'{iso_files.name}' is not a directory!")
        return

    with open(filelist, "r") as f:
        lines = f.readlines()

    inode_data: list[FileListData] = []
    for line in lines[:-1]:
        l = [x for x in line.split("|") if x]
        p = Path(l[1])
        inode_data.append(FileListData(Path(*p.parts[1:]), int(l[0]), 0))

    if lines[-1].startswith("//") is False:
        print(f"Could not to find the '{filelist.name}' inode total!")
        return

    iso_info = FileListInfo(inode_data, int(lines[-1][2:]))

    with open(iso, "rb") as f:
        header = f.read(0xF60000)
        i = 0
        data_start = -1
        for lba in range(7862):
            udf_check = struct.unpack_from("<269x18s1761x", header, lba * 0x800)[0]
            if udf_check == b"*UDF DVD CGMS Info":
                i += 1

            if i == iso_info.total_inodes + 1:
                data_start = (lba + 1) * 0x800
                break
        else:
            print(
                "ERROR: Couldn't get all the UDF file chunk, original tool would've looped here"
            )
            print("Closing instead...")
            return

        f.seek(-0x800, 2)
        footer = f.read(0x800)

    with open(output, "wb+") as f:
        f.write(header[:data_start])

        for inode in inode_data:
            fp = iso_files / inode.path
            start_pos = f.tell()
            if fp.exists() is False:
                print(f"File '{inode.path}' not found!")
                return

            print(f"Inserting {str(inode.path)}...")

            with open(fp, "rb") as g:
                while data := g.read(0x80000):
                    f.write(data)

            end_pos = f.tell()

            # Align to next LBA
            al_end = (end_pos + 0x7FF) & ~(0x7FF)
            f.write(b"\x00" * (al_end - end_pos))

            end_save = f.tell()

            new_lba = start_pos // 0x800
            new_size = end_pos - start_pos
            f.seek(inode.inode + 2)

            f.write(struct.pack("<I", new_lba))
            f.write(struct.pack(">I", new_lba))
            f.write(struct.pack("<I", new_size))
            f.write(struct.pack(">I", new_size))

            f.seek(end_save)

        # Align to 0x8000
        end_pos = f.tell()
        al_end = (end_pos + 0x7FFF) & ~(0x7FFF)
        f.write(b"\x00" * (al_end - end_pos))

        # Sony's cdvdgen tool starting with v2.00 by default adds
        # a 20MiB padding to the end of the PVD, add it here if requested
        # minus a whole LBA for the end of file Anchor
        if add_padding:
            f.write(b"\x00" * (0x140_0000 - 0x800))

        # Last LBA includes the anchor
        last_pvd_lba = (f.tell() // 0x800) + 1

        f.write(footer)
        f.seek(0x8050)
        f.write(struct.pack("<I", last_pvd_lba))
        f.write(struct.pack(">I", last_pvd_lba))
        f.seek(-0x7F4, 2)
        f.write(struct.pack("<I", last_pvd_lba))


if __name__ == "__main__":
    main()
