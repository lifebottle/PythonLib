from pywinauto import application
from pywinauto.keyboard import send_keys
from pywinauto.findwindows import find_windows

app = application.Application(backend="uia").start('apache3.exe')
app = application.Application(backend="uia").connect(title='Apache3 Build 3.10.6 (BETA)')

#Get the window about FREE license
app.Information.set_focus()
send_keys('{ENTER}')

#Get the window about Drive missing
drive_missing = app.Apache3Build.child_window(title="apache3", control_type="Window")
drive_missing.set_focus()
send_keys('{ENTER}')

#app.Apache3Build.print_control_identifiers()

#Click on the Open Iso button
app.Apache3Build.child_window(auto_id="1011").click()

app.Dialog.child_window(auto_id="2").click()

app.Apache3Build.child_window()
app.Apache3Build.child_window(auto_id="TitleBar").print_control_identifiers()

open_ele = app.Apache3Build.child_window(title="Open", auto_id="1011", control_type="Button")
open_ele.click_input()