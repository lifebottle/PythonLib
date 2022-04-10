import os
import requests
import json
import subprocess

def get_Releases(org, repo_name, latest=False):
    
    #git_url = "https://api.github.com/repos/SymphoniaLauren/Tales-of-Rebirth/releases"
    git_url = "https://api.github.com/repos/{}/{}/releases".format(org, repo_name)
    
    if latest:
        git_url = git_url+"/latest"
        
    header = {
        "Accept":"application/vnd.github.v3+json" 
    }

    res = requests.get(git_url)
    json_res = json.loads(res.text)
    
    return json_res


def refresh_repo(repo_name):   
    
    base_path = os.path.join(os.getcwd(), "..", repo_name)
    print("Repo to refresh: {}".format(base_path))
    listFile = subprocess.run(
            ["git", "pull", repo_name],
            cwd=base_path
    )
