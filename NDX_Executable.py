import ToolsNDX
import sys
import os

if __name__ == "__main__":
    
    operation = sys.argv[1]
    choices   = sys.argv[2]
    
    tool = ToolsNDX.ToolsNDX("TBL_All.json")
    if operation == "-d":
        
        if choices == "Iso":
            
            path = sys.argv[3]
            tool.extract_Iso(path)
            tool.extract_Main_Archive()
            
        elif choices == "Story":
            
            tool.extract_All_Story(True)
            
        elif choices == "Skit":
            
            tool.extract_All_Skit(True)
        
            
            