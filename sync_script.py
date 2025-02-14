import os
import json
import yaml
import git
from github import Github
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def convert_yaml_to_json(yaml_file):
    """Converts a YAML file to JSON format (used internally)."""
    with open(yaml_file, 'r') as file:
        yaml_data = yaml.safe_load(file)
    return yaml_data

def update_yaml_file(yaml_file, updated_data):
    """Writes updated data back to the YAML file and adds a comment."""
    with open(yaml_file, 'w') as file:
        file.write("# Updated the version based on trial.yaml\n")
        yaml.dump(updated_data, file, default_flow_style=False)

def get_tag_paths(repo_path, file_extension=".yaml"):
    """Finds YAML files containing a 'tag' field in a given repo."""
    tag_paths = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(file_extension):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    yaml_data = yaml.safe_load(f)
                    if yaml_data and 'tag' in yaml_data:
                        tag_paths.append(file_path)
    return tag_paths

def sync_tag_values(work_yaml, trial_yaml):
    """Syncs 'tag' field from trial YAML to work YAML if they differ."""
    work_data = convert_yaml_to_json(work_yaml)
    trial_data = convert_yaml_to_json(trial_yaml)
    
    if work_data.get("tag") != trial_data.get("tag"):
        work_data["tag"] = trial_data["tag"]
        update_yaml_file(work_yaml, work_data)
        return True  # Changes were made
    return False  # No changes needed

def raise_pull_request(repo_path, client_name, service_name, github_token):
    """Creates a GitHub pull request after updating tag values."""
    repo = git.Repo(repo_path)
    branch_name = f"chore/{client_name}-update-{service_name}"
    
    repo.git.checkout('-b', branch_name)
    repo.git.add(A=True)
    repo.git.commit('-m', f"chore({client_name}): updated {service_name} tag")
    repo.git.push('--set-upstream', 'origin', branch_name)
    
    github = Github(github_token)
    repo_name = repo.remotes.origin.url.split('.git')[0].split('/')[-1]
    user = github.get_user()
    github_repo = user.get_repo(repo_name)
    
    pr = github_repo.create_pull(
        title=f"chore({client_name}): updated {service_name} tag",
        body="Automated PR to sync tag values.",
        head=branch_name,
        base="main"
    )
    
    return pr.html_url

if __name__ == "__main__":
    work_repo = os.getenv("WORK_REPO", "path/to/work/repo")
    trial_repo = os.getenv("TRIAL_REPO", "path/to/trial/repo")
    github_token = os.getenv("GITHUB_TOKEN", "fake_token_for_local_test")
    client_name = os.getenv("CLIENT_NAME", "client-name")
    service_name = os.getenv("SERVICE_NAME", "service-name")
    testing_mode = False  # Set to False to push to GitHub

    work_paths = get_tag_paths(work_repo)
    trial_paths = get_tag_paths(trial_repo)
    
    for work_path, trial_path in zip(work_paths, trial_paths):
        if sync_tag_values(work_path, trial_path):
            print(f"Updated {work_path} with new tag from {trial_path}.")
            if not testing_mode:
                pr_url = raise_pull_request(work_repo, client_name, service_name, github_token)
                print(f"Pull Request created: {pr_url}")
            else:
                print("Tag values synced, but PR creation skipped for testing.")
