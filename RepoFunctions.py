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
    
    return top5
    
def get_pull_requests_message(org, repo_name):
    
    #Get Datas
    top5_prs = get_pull_requests(org, repo_name)
    
    message ='Here are the PRs recently : '
    
    for pr in top5_prs:
    
        message = message + "<br>"
        message += '{} - {} by {} ... {}'.format(pr['created_at'], pr['title'], pr['user']['login'], pr['_links']['html']['href'])
        
    return message
        
        
    
    
    
    