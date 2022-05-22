import os
import requests
import json
import subprocess
import pandas as pd

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
            ["git", "pull"],
            cwd=base_path
    )
    
def get_pull_requests(org, repo_name):
    api_url = "https://api.github.com/repos/{}/{}/pulls?state=all".format(org, repo_name)

    header = {
        "Accept":"application/vnd.github.v3+json" 
    }

    res = requests.get(api_url)
    json_res = json.loads(res.text)
    
    #Taking Top 5 PR
    top5 = json_res[0:5]
    
    top5_infos = pd.DataFrame([ [ele['created_at'], ele['title'], ele['state'], ele['user']['login'], ele['url']] for ele in top5], columns = ['Created', 'Title', 'Status', 'User', 'Url'])
    
    
