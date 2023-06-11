import re
import pandas as pd
import os
import pygsheets
import lxml.etree as etree
from requests import HTTPError

# Replace n occurences of a string starting from the right
def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def add_line_break(text):
    temp = ""
    currentLineSize = 0

    text_size = len(text)
    max_size = 32
    split_space = text.split(" ")

    for word in split_space:
        currentLineSize += (len(word) + 1)

        if currentLineSize <= max_size:
            temp = temp + word + ' '

        else:
            temp = temp + '\n' + word + ' '
            currentLineSize = 0

    temp = temp.replace(" \n", "\n")
    temp = rreplace(temp, " ", "", 1)

    return temp
def clean_text(text):
    text = re.sub(r"\n ", "\n", text)
    text = re.sub(r"\n", "", text)
    text = re.sub(r"(<\w+:?\w+>)", "", text)
    text = re.sub(r"\[\w+=*\w+\]", "", text)
    text = re.sub(r" ", "", text)
    text = re.sub(u'\u3000', '', text)
    text = re.sub(r" ", "", text)
    return text


def extract_Google_Sheets(googlesheet_id, sheet_name):
    
    creds_path = r"..\gsheet.json"
    
    if os.path.exists(creds_path):      
        
        try:
            gc = pygsheets.authorize(service_file=creds_path)
            sh = gc.open_by_key(googlesheet_id)
            sheets = sh.worksheets()
            id_sheet = [ ele.index for ele in sheets if ele.title == sheet_name ]
            
            if len(id_sheet) > 0:
                wks = sh[id_sheet[0]]
                df = pd.DataFrame(wks.get_all_records())
                
                if len(df) > 0:
                    return df
                else:
                    print("Python didn't find any table with rows in this sheet")
                        
            else:
                print("{} was not found in the googlesheet {}".format(sheet_name, googlesheet_id))
                    
        except HTTPError as e:
            print(e)         
    
    else:
        print("{} was not found to authenticate to Googlesheet API".format(creds_path))


# Extract/Transform Lauren translation
def extract_Lauren_Translation():

    # Load Lauren's googlesheet data inside a dataframe
    df = extract_Google_Sheets("1-XwzS7F0SaLlXwv1KS6RcTEYYORH2DDb1bMRy5VM5oo", "Story")

    # 1) Make some renaming and transformations
    df = df.rename(columns={"KEY": "File", "Japanese": "JapaneseText", "Lauren's Script": "EnglishText"})

    # 2) Filter only relevant rows and columns from the googlesheet
    df = df.loc[(df['EnglishText'] != "") & (df['JapaneseText'] != ""), :]
    df = df[['File', 'JapaneseText', 'EnglishText']]

    # 3) Make some transformations to the JapaneseText so we can better match with XML
    df['File'] = df['File'].apply(lambda x: x.split("_")[0] + ".xml")
    df['JapaneseText'] = df['JapaneseText'].apply(lambda x: clean_text(x))
    return df

# Transfer Lauren translation
def transfer_Lauren_Translation():

    df_lauren = extract_Lauren_Translation()

    # Distinct list of XMLs file
    xml_files = list(set(df_lauren['File'].tolist()))

    for file in xml_files:
        cond = df_lauren['File'] == file
        lauren_translations = dict(df_lauren[cond][['JapaneseText', 'EnglishText']].values)
        file_path = self.story_XML_new + 'XML/' + file

        if os.path.exists(file_path):
            tree = etree.parse(file_path)
            root = tree.getroot()
            need_save = False

            for key, item in lauren_translations.items():

                for entry_node in root.iter("Entry"):
                    xml_jap = entry_node.find("JapaneseText").text or ''
                    xml_eng = entry_node.find("EnglishText").text or ''
                    xml_jap_cleaned = clean_text(xml_jap)

                    if key == xml_jap_cleaned:
                        item = add_line_break(item)

                        if xml_eng != item:
                            entry_node.find("EnglishText").text = item
                            need_save = True

                            if entry_node.find("Status").text == "To Do":
                                entry_node.find("Status").text = "Editing"

                    # else:
                    #    print("File: {} - {}".format(file, key))

            if need_save:
                txt = etree.tostring(root, encoding="UTF-8", pretty_print=True, xml_declaration=False)

                with open(file_path, 'wb') as xml_file:
                    xml_file.write(txt)

        else:
            print("File {} skipped because file is not found".format(file))    # Replace n occurences of a string starting from the right
