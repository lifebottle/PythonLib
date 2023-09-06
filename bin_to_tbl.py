import json

big_ass_array = []
TBL_BIN_PATH = "./00014.bin"

with open(TBL_BIN_PATH, "rb") as f:
    while cp := f.read(2):
        cp = cp[::-1]
        big_ass_array.append(cp.decode("cp932"))

data = dict()
for index in range(len(big_ass_array)):

    btm = (index % 0xBB) + 0x40
    if 0x5B < btm:
        btm += 1
    if 0x7E < btm:
        btm += 1

    top = (index // 0xBB) + 0x99
    if 0x9F < top:
        top += 0x40

    character = btm | (top << 8)

    data[f"{character:X}"] = big_ass_array[index]

with open("tbl.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
