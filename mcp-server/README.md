# Synm MCP Server

Model Context Protocol server for Synm Personal AI Vault. Allows Claude Desktop to access your vault memory.

## Installation

```bash
cd mcp-server
npm install
npm run build
```

## Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "synm": {
      "command": "node",
      "args": ["/path/to/synm/mcp-server/build/index.js"],
      "env": {
        "SYNM_API_URL": "https://synm.app.vd",
        "SYNM_API_TOKEN": "your-mediator-pat-here"
      }
    }
  }
}
```

Replace `/path/to/synm` with the actual path to your Synm repo.

## Usage

Once configured, Claude Desktop will have access to three tools:

1. **synm_create_session** - Create a session with your vault
2. **synm_get_context** - Retrieve memories based on a prompt
3. **synm_list_scopes** - List available data scopes

Example conversation:
```
You: Create a session with my Synm vault
Claude: [calls synm_create_session]

You: What's my bio?
Claude: [calls synm_get_context with prompt="user bio"]
```

## Tools

### synm_create_session
Creates a session with the vault. Required before accessing any data.

**Parameters:**
- `profile` (optional): Profile to use (default: "work")

### synm_get_context
Retrieves context from the vault based on your prompt.

**Parameters:**
- `prompt` (required): What you're looking for
- `scopes` (optional): Array of scopes to search (default: ["bio.basic", "projects.recent"])

### synm_list_scopes
Lists available scopes in the current profile.

## Development

```bash
# Watch mode for development
npm run watch
```
