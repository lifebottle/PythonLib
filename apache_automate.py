from pywinauto import application
from pywinauto.keyboard import send_keys
from pywinauto import mouse
from pywinauto.findwindows import find_windows
import os
import shutil

def open_apache3_iso(repo_name):
    
    app = application.Application(backend="uia").start('apache3.exe')
    app = application.Application(backend="uia").connect(title='Apache3 Build 3.10.6 (BETA)')
    
    #Get the window about FREE license
    app.Information.set_focus()
    send_keys('{ENTER}')
    
    #Get the window about Drive missing
    drive_missing = app.Apache3Build.child_window(title="apache3", control_type="Window")
    drive_missing.set_focus()
    send_keys('{ENTER}')
    
    iso_path = os.path.join( os.path.normpath(os.getcwd() + os.sep + os.pardir), "Data",repo_name,"Disc","New","{}.iso".format(repo_name))

    #Click on the Open Iso button
    app.Apache3Build.child_window(auto_id="1011").click()
    
    #File Name textbox
    text_box_filename = app.Dialog.child_window(auto_id="1152").wrapper_object()
    text_box_filename.type_keys(r"{}".format(iso_path))
    
    #Open the iso
    app.Dialog.child_window(title="Open", auto_id="1", control_type="Button").wrapper_object().click()

    return app

def locate_right_click(file_name, app):
    item = app.Apache3Build.child_window(title=file_name, control_type="ListItem").wrapper_object()
    pos_x = item.rectangle().mid_point().x
    pos_y = item.rectangle().mid_point().y
    app.Apache3Build.set_focus()
    mouse.click(button='right', coords=(pos_x, pos_y))
    
def browse_replace_file(file_replace_ele, new_file_path, repo_name):
    
    #Browse the file and put the new file path
    new_file_path = os.path.join( os.path.normpath(os.getcwd() + os.sep + os.pardir), "Data",repo_name, "Menu", "New", "SLPS_254.50")
    file_replace_ele.child_window(auto_id="1095").wrapper_object().click()
    file_replace_ele.Dialog.child_window(title="File name:", auto_id="1152", control_type="Edit").wrapper_object().type_keys(new_file_path)
    file_replace_ele.Dialog.child_window(title="Open", auto_id="1", control_type="Button").wrapper_object().click()
    
    #Click on the Replace File button
    file_replace_ele.child_window(title="Replace File", auto_id="1094", control_type="Button").wrapper_object().click()
    
    
def replace_files(files_list, app):
    
    new_file_path_format = os.path.join( os.path.normpath(os.getcwd() + os.sep + os.pardir), "Data",repo_name, "Disc", "New")
    for file_name in files_list:

        #Locate file and right-click it
        locate_right_click(file_name, app)

        #Click on the option "Replace Selected File"
        replace_file_pos = app.Context.child_window(title="Replace Selected File", auto_id="32782", control_type="MenuItem").wrapper_object().rectangle().mid_point()
        mouse.click(button='left', coords=(replace_file_pos.x, replace_file_pos.y))
        
        file_replace_ele = app.Apache3Build.Apache3FileReplacer
        
        #Uncheck TOC and Check Ignore File size
        file_replace_ele.child_window(title="Update TOC", auto_id="1092", control_type="CheckBox").wrapper_object().click()
        file_replace_ele.child_window(title="Ignore File Size Differences", auto_id="1093", control_type="CheckBox").click()

        browse_replace_file(file_replace_ele, os.path.join(new_file_path_format, file_name), repo_name)
      

#Files to reinsert
#files_list = ['SLPS_254.50', 'DAT.bin']
files_list = ['SLPS_254.50']

repo_name = "Tales-Of-Rebirth"

#copy original Iso
original_path = os.path.join(os.getcwd(), "..", "Data", repo_name, "Disc", "Original", "{}.iso".format(repo_name))
new_path = os.path.join(os.getcwd(), "..", "Data", repo_name, "Disc", "New", "{}.iso".format(repo_name))

print("Copy Original Iso into New folder")
shutil.copy( original_path, new_path)



try:
    app = application.Application(backend="uia").connect(title='Apache3 Build 3.10.6 (BETA)')
    app.Apache3Build.close()
    
except:
    print("Open Apache3 and load the iso")
    app = open_apache3_iso(repo_name)

    print("Replace the different files")
    replace_files(files_list,app)
    
    print("Close Apache3")
    app.Apache3Build.close()