import pandas as pd

with open("TBL_PhantasiaX.txt", "r", encoding="utf-8") as f:
    data =f.readlines()

final_list = []

with open("TOPX.tbl", "w", encoding="utf-8") as f:
    for line in data:
        splited = line.replace(" ","").replace("\n","").split(";")
        hex_value = splited[0]
        jap_text = splited[-1]
        f.write(hex_value+"="+jap_text+"\n")


df = pd.DataFrame(final_list, columns = ['Hex', 'Japanese'])
df.to_excel("TOPX_table.xlsx")