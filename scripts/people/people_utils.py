from git import Repo, GitCommandError
import logging

log = logging.getLogger(__name__)


def clone_repository(repo_url, clone_dir):
    """
    Clone a git repository to a specific directory.

    :param repo_url: The URL of the git repository to clone.
    :param clone_dir: The directory where the repository will be cloned.
    """
    try:
        print(f"Cloning repository from {repo_url} to {clone_dir}...")
        Repo.clone_from(repo_url, clone_dir)
        print("Repository cloned successfully.")
    except GitCommandError as e:
        if e.status == 128:
            log.info("Repo directory non-empty, assuming it already exists.")
            return
    except Exception as e:
        print(f"An error occurred: {e}")