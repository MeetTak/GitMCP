#!/usr/bin/env python3
"""
Git Repository Manager MCP Server - Secure git operations for multiple repositories
"""
import os
import sys
import logging
import subprocess
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("gitrepo-server")

# Initialize MCP server
mcp = FastMCP("gitrepo")

# Configuration
REPOS_BASE_PATH = os.environ.get("GIT_REPOS_PATH", "/repos")
MAX_OUTPUT_LENGTH = 10000
GIT_TIMEOUT = 30

# === UTILITY FUNCTIONS ===

def sanitize_path(path: str) -> str:
    """Sanitize and validate repository path."""
    if not path or not path.strip():
        return ""
    
    # Remove dangerous characters
    sanitized = re.sub(r'[;&|`$(){}]', '', path.strip())
    
    # Remove path traversal attempts
    sanitized = sanitized.replace('..', '')
    
    return sanitized

def get_repo_path(repo_name: str) -> str:
    """Get absolute path to repository with validation."""
    if not repo_name or not repo_name.strip():
        return ""
    
    sanitized = sanitize_path(repo_name)
    if not sanitized:
        return ""
    
    # Build absolute path
    repo_path = Path(REPOS_BASE_PATH) / sanitized
    
    # Ensure it's within base path
    try:
        repo_path = repo_path.resolve()
        base_path = Path(REPOS_BASE_PATH).resolve()
        
        if not str(repo_path).startswith(str(base_path)):
            return ""
        
        return str(repo_path)
    except Exception:
        return ""

def run_git_command(repo_path: str, args: str, timeout: int = GIT_TIMEOUT) -> str:
    """Execute a git command safely in the specified repository."""
    if not repo_path or not os.path.isdir(repo_path):
        return "❌ Error: Invalid repository path"
    
    # Check if it's a git repository
    git_dir = Path(repo_path) / ".git"
    if not git_dir.exists():
        return "❌ Error: Not a git repository"
    
    try:
        cmd = ["git", "-C", repo_path] + args.split()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout if result.stdout else result.stderr
        
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + f"\n\n... [Output truncated. Total: {len(output)} chars]"
        
        if result.returncode == 0:
            return output if output.strip() else "✅ Command completed successfully"
        else:
            return f"⚠️ Git command completed with status {result.returncode}:\n{output}"
            
    except subprocess.TimeoutExpired:
        return f"⏱️ Command timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"Git command error: {e}")
        return f"❌ Error executing git command: {str(e)}"

def truncate_output(output: str) -> str:
    """Truncate long output."""
    if len(output) > MAX_OUTPUT_LENGTH:
        return output[:MAX_OUTPUT_LENGTH] + f"\n\n... [Truncated from {len(output)} chars]"
    return output

# === MCP TOOLS ===

@mcp.tool()
async def list_repos(filter_name: str = "") -> str:
    """List all git repositories in the configured base path with optional name filtering."""
    logger.info("Listing repositories")
    
    try:
        base = Path(REPOS_BASE_PATH)
        
        if not base.exists():
            return f"❌ Base path does not exist: {REPOS_BASE_PATH}"
        
        repos = []
        for item in base.iterdir():
            if item.is_dir():
                git_dir = item / ".git"
                if git_dir.exists():
                    if not filter_name.strip() or filter_name.strip().lower() in item.name.lower():
                        repos.append(item.name)
        
        if not repos:
            return "📁 No git repositories found"
        
        repos.sort()
        repo_list = "\n".join([f"  - {repo}" for repo in repos])
        
        return f"📁 Found {len(repos)} repositories:\n{repo_list}"
        
    except Exception as e:
        logger.error(f"Error listing repos: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
async def repo_status(repo_name: str = "") -> str:
    """Get the git status of a repository showing modified, staged, and untracked files."""
    logger.info(f"Getting status for {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    result = run_git_command(repo_path, "status")
    
    return f"📊 Status for {repo_name}:\n\n{result}"

@mcp.tool()
async def repo_log(repo_name: str = "", limit: str = "10") -> str:
    """View commit history of a repository with optional limit on number of commits shown."""
    logger.info(f"Getting log for {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    try:
        limit_int = int(limit) if limit.strip() else 10
        if limit_int < 1 or limit_int > 100:
            limit_int = 10
    except ValueError:
        limit_int = 10
    
    result = run_git_command(repo_path, f"log --oneline -n {limit_int}")
    
    return f"📜 Last {limit_int} commits for {repo_name}:\n\n{result}"

@mcp.tool()
async def repo_branches(repo_name: str = "") -> str:
    """List all branches in a repository showing current branch and all available branches."""
    logger.info(f"Getting branches for {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    result = run_git_command(repo_path, "branch -a")
    
    return f"🌿 Branches for {repo_name}:\n\n{result}"

@mcp.tool()
async def repo_diff(repo_name: str = "", file_path: str = "") -> str:
    """Show uncommitted changes in a repository or specific file showing line-by-line differences."""
    logger.info(f"Getting diff for {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    if file_path.strip():
        sanitized_file = sanitize_path(file_path)
        if not sanitized_file:
            return "❌ Error: Invalid file path"
        result = run_git_command(repo_path, f"diff {sanitized_file}")
        target = f"file {sanitized_file}"
    else:
        result = run_git_command(repo_path, "diff")
        target = "repository"
    
    if not result.strip() or result == "✅ Command completed successfully":
        return f"✅ No changes in {target}"
    
    return f"📝 Changes in {repo_name} ({target}):\n\n{result}"

@mcp.tool()
async def repo_remote(repo_name: str = "") -> str:
    """Show remote repository URLs configured for a repository including fetch and push URLs."""
    logger.info(f"Getting remotes for {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    result = run_git_command(repo_path, "remote -v")
    
    if not result.strip() or result == "✅ Command completed successfully":
        return f"🌐 No remotes configured for {repo_name}"
    
    return f"🌐 Remotes for {repo_name}:\n\n{result}"

@mcp.tool()
async def repo_current_branch(repo_name: str = "") -> str:
    """Get the currently checked out branch name in a repository."""
    logger.info(f"Getting current branch for {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    result = run_git_command(repo_path, "branch --show-current")
    
    if result.strip() and not result.startswith("❌") and not result.startswith("⚠️"):
        return f"🌿 Current branch: {result.strip()}"
    
    return result

@mcp.tool()
async def repo_show_commit(repo_name: str = "", commit_hash: str = "") -> str:
    """Show details of a specific commit including changes made using commit hash."""
    logger.info(f"Showing commit {commit_hash} for {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    if not commit_hash.strip():
        return "❌ Error: Commit hash is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    # Validate commit hash format (alphanumeric only)
    sanitized_hash = re.sub(r'[^a-fA-F0-9]', '', commit_hash.strip())
    if not sanitized_hash:
        return "❌ Error: Invalid commit hash format"
    
    result = run_git_command(repo_path, f"show {sanitized_hash}")
    
    return f"📝 Commit {sanitized_hash} in {repo_name}:\n\n{result}"

@mcp.tool()
async def repo_file_history(repo_name: str = "", file_path: str = "", limit: str = "10") -> str:
    """Show commit history for a specific file in a repository with optional limit."""
    logger.info(f"Getting file history for {file_path} in {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    if not file_path.strip():
        return "❌ Error: File path is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    sanitized_file = sanitize_path(file_path)
    if not sanitized_file:
        return "❌ Error: Invalid file path"
    
    try:
        limit_int = int(limit) if limit.strip() else 10
        if limit_int < 1 or limit_int > 100:
            limit_int = 10
    except ValueError:
        limit_int = 10
    
    result = run_git_command(repo_path, f"log --oneline -n {limit_int} -- {sanitized_file}")
    
    return f"📜 History for {sanitized_file} in {repo_name}:\n\n{result}"

@mcp.tool()
async def repo_search(repo_name: str = "", search_term: str = "") -> str:
    """Search for text in tracked files within a repository using git grep."""
    logger.info(f"Searching for '{search_term}' in {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    if not search_term.strip():
        return "❌ Error: Search term is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    # Escape special characters for grep
    escaped_term = search_term.strip().replace('"', '\\"')
    
    result = run_git_command(repo_path, f'grep -n "{escaped_term}"')
    
    if "fatal:" in result.lower() or not result.strip():
        return f"🔍 No matches found for '{search_term}' in {repo_name}"
    
    return f"🔍 Search results for '{search_term}' in {repo_name}:\n\n{truncate_output(result)}"

@mcp.tool()
async def repo_stats(repo_name: str = "") -> str:
    """Get repository statistics including total commits, contributors, and file counts."""
    logger.info(f"Getting stats for {repo_name}")
    
    if not repo_name.strip():
        return "❌ Error: Repository name is required"
    
    repo_path = get_repo_path(repo_name)
    if not repo_path:
        return "❌ Error: Invalid repository name"
    
    try:
        # Get commit count
        commit_count = run_git_command(repo_path, "rev-list --count HEAD")
        
        # Get contributor count
        contributors = run_git_command(repo_path, "shortlog -sn --all")
        contributor_lines = [line for line in contributors.split('\n') if line.strip()]
        contributor_count = len(contributor_lines)
        
        # Get branch count
        branches = run_git_command(repo_path, "branch -a")
        branch_lines = [line for line in branches.split('\n') if line.strip()]
        branch_count = len(branch_lines)
        
        stats = f"""📊 Repository Statistics for {repo_name}:

📝 Total Commits: {commit_count.strip()}
👥 Contributors: {contributor_count}
🌿 Branches: {branch_count}

Top Contributors:
{chr(10).join(contributor_lines[:5])}"""
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return f"❌ Error: {str(e)}"

# === SERVER STARTUP ===
if __name__ == "__main__":
    logger.info("Starting Git Repository Manager MCP server...")
    logger.info(f"Repository base path: {REPOS_BASE_PATH}")
    
    if not os.path.exists(REPOS_BASE_PATH):
        logger.warning(f"Base path does not exist: {REPOS_BASE_PATH}")
    
    try:
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)