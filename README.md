# Git MCP Server Setup Guide

This guide will help you set up a custom Git MCP server with Docker Desktop's MCP integration.

## Prerequisites

- Docker Desktop with MCP support
- Claude Desktop application
- A directory containing your git repositories

## Setup Instructions

### 1. Build the Docker Image

```bash
docker build -t git-mcp-server .
```

### 2. Create Custom Catalog Directory

```bash
mkdir -p ~/.docker/mcp/catalogs/
```

### 3. Create Custom Catalog File

```bash
touch ~/.docker/mcp/catalogs/mycustomcatalog.yaml
```

### 4. Edit the Custom Catalog File

```bash
nano ~/.docker/mcp/catalogs/mycustomcatalog.yaml
```

Add the following content (replace the hostPath with your actual repos directory):

```yaml
version: 2
name: custom
displayName: Custom MCP Servers
registry:
  gitrepo:
    description: "Secure git repository manager for viewing status, history, branches, and searching code"
    title: "Git Repository Manager"
    type: server
    dateAdded: "2025-10-05T00:00:00Z"
    image: gitrepo-mcp-server:latest
    ref: ""
    readme: ""
    toolsUrl: ""
    source: ""
    upstream: ""
    icon: ""
    volumes:
      - hostPath: "$HOME/repos"
        containerPath: "/repos"
        readOnly: true
    tools:
      - name: list_repos
      - name: repo_status
      - name: repo_log
      - name: repo_branches
      - name: repo_diff
      - name: repo_remote
      - name: repo_current_branch
      - name: repo_show_commit
      - name: repo_file_history
      - name: repo_search
      - name: repo_stats
    metadata:
      category: productivity
      tags:
        - git
        - development
        - version-control
        - repositories
      license: MIT
      owner: local
```

**IMPORTANT:** Replace `$HOME/repos` with the actual path to your git repositories directory.

### 5. Update Registry File

```bash
nano ~/.docker/mcp/registry.yaml
```

Add the gitrepo entry under the registry section:

```yaml
registry:
  gitrepo:
    ref: ""
```

### 6. Update Claude Desktop Configuration

Edit your Claude Desktop configuration file:

**macOS:**
```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

Add or update with the following configuration:

```json
{
  "mcpServers": {
    "mcp-toolkit-gateway": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "/var/run/docker.sock:/var/run/docker.sock",
        "-v",
        "$HOME/.docker/mcp:/mcp",
        "docker/mcp-gateway",
        "--catalog=/mcp/catalogs/docker-mcp.yaml",
        "--catalog=/mcp/catalogs/mycustomcatalog.yaml",
        "--config=/mcp/config.yaml",
        "--registry=/mcp/registry.yaml",
        "--tools-config=/mcp/tools.yaml",
        "--transport=stdio"
      ]
    }
  }
}
```

**Note:** On Windows, replace `$HOME` with your actual user path or use `%USERPROFILE%`.

### 7. Restart Claude Desktop

```bash
# 1. Quit Claude Desktop completely (Cmd+Q on macOS, Alt+F4 on Windows)

# 2. Stop the gateway container
docker stop $(docker ps -q --filter ancestor=docker/mcp-gateway)

# 3. Start Claude Desktop again

# 4. Wait 15 seconds for initialization

# 5. Verify the server is registered
docker mcp server list
```

Expected output should show: `dice, gitrepo`

## Available Tools

Once configured, the following git operations will be available through Claude:

- `list_repos` - List all repositories
- `repo_status` - Check repository status
- `repo_log` - View commit history
- `repo_branches` - List branches
- `repo_diff` - View differences
- `repo_remote` - View remote information
- `repo_current_branch` - Show current branch
- `repo_show_commit` - Display commit details
- `repo_file_history` - View file history
- `repo_search` - Search code
- `repo_stats` - Repository statistics

## Troubleshooting

If the server doesn't appear:

1. Check Docker is running: `docker ps`
2. Verify the image exists: `docker images | grep git-mcp-server`
3. Check catalog syntax: `cat ~/.docker/mcp/catalogs/mycustomcatalog.yaml`
4. Review Claude Desktop logs for errors
5. Ensure the repos directory path is correct and accessible
