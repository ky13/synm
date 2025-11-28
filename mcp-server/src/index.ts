#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import axios from "axios";

// Configuration
const SYNM_API_URL = process.env.SYNM_API_URL || "https://synm.app.vd";
const SYNM_API_TOKEN = process.env.SYNM_API_TOKEN || "";

if (!SYNM_API_TOKEN) {
  console.error("Error: SYNM_API_TOKEN environment variable is required");
  process.exit(1);
}

// Axios instance with default config
const synmClient = axios.create({
  baseURL: SYNM_API_URL,
  headers: {
    Authorization: `Bearer ${SYNM_API_TOKEN}`,
    "Content-Type": "application/json",
  },
  httpsAgent: new (await import("https")).Agent({
    rejectUnauthorized: false, // For self-signed certs in local dev
  }),
});

// Session management
let currentSession: { id: string; profile: string; expiresAt: string } | null = null;

// Create MCP server
const server = new Server(
  {
    name: "synm-mcp-server",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "synm_create_session",
        description: "Create a new session with Synm vault for accessing memory. Required before getting context.",
        inputSchema: {
          type: "object",
          properties: {
            profile: {
              type: "string",
              description: "Profile to use (e.g., 'work', 'public')",
              default: "work",
            },
          },
        },
      },
      {
        name: "synm_get_context",
        description: "Retrieve relevant context from Synm vault based on a prompt. Returns memories, bio, projects, etc.",
        inputSchema: {
          type: "object",
          properties: {
            prompt: {
              type: "string",
              description: "What you're looking for (e.g., 'user bio', 'recent projects', 'technical skills')",
            },
            scopes: {
              type: "array",
              items: { type: "string" },
              description: "Scopes to search (e.g., ['bio.basic', 'projects.recent', 'resume.public'])",
              default: ["bio.basic", "projects.recent"],
            },
          },
          required: ["prompt"],
        },
      },
      {
        name: "synm_list_scopes",
        description: "List available scopes in the configured profile",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "synm_create_session": {
        const profile = (args?.profile as string) || "work";

        const response = await synmClient.post("/v1/session", { profile });
        currentSession = {
          id: response.data.session_id,
          profile: response.data.profile,
          expiresAt: response.data.expires_at,
        };

        return {
          content: [
            {
              type: "text",
              text: `Session created!\nID: ${currentSession.id}\nProfile: ${currentSession.profile}\nExpires: ${currentSession.expiresAt}`,
            },
          ],
        };
      }

      case "synm_get_context": {
        if (!currentSession) {
          return {
            content: [
              {
                type: "text",
                text: "No active session. Please create a session first using synm_create_session.",
              },
            ],
            isError: true,
          };
        }

        const prompt = args?.prompt as string;
        const scopes = (args?.scopes as string[]) || ["bio.basic", "projects.recent"];

        const response = await synmClient.post("/v1/context", {
          session_id: currentSession.id,
          profile: currentSession.profile,
          scopes,
          prompt,
        });

        const context = response.data.context;
        const citations = response.data.citations;

        let result = `**Context from Synm Vault:**\n\n${context}\n\n`;

        if (citations && citations.length > 0) {
          result += `\n**Sources:**\n`;
          citations.forEach((cite: any) => {
            result += `- ${cite.type}: ${cite.ref}${cite.score ? ` (relevance: ${(parseFloat(cite.score) * 100).toFixed(1)}%)` : ""}\n`;
          });
        }

        return {
          content: [
            {
              type: "text",
              text: result,
            },
          ],
        };
      }

      case "synm_list_scopes": {
        // For now, return the known scopes from the example policy
        const knownScopes = [
          "bio.basic - Basic biographical information",
          "projects.recent - Recent project work",
          "resume.public - Public resume/CV information",
        ];

        return {
          content: [
            {
              type: "text",
              text: `**Available scopes (work profile):**\n\n${knownScopes.join("\n")}`,
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: "text",
              text: `Unknown tool: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error: any) {
    return {
      content: [
        {
          type: "text",
          text: `Error calling Synm API: ${error.response?.data?.detail || error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Synm MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
