import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { logToDiscord } from "./logger.service.js";

let mcpClient = null;
let mcpToolsCache = [];

export async function initMcpClient() {
    if (mcpClient) return;

    try {
        console.log("[MCP] Initializing MCP Client...");

        // On Windows, use npx.cmd to avoid ENOENT errors in child_process spawn
        const command = process.platform === 'win32' ? 'npx.cmd' : 'npx';

        const transport = new StdioClientTransport({
            command: command,
            args: ["-y", "@modelcontextprotocol/server-filesystem", "D:\\"]
        });

        mcpClient = new Client({
            name: "grace-mcp-client",
            version: "1.0.0"
        }, {
            capabilities: {
                tools: {}
            }
        });

        await mcpClient.connect(transport);
        console.log("[MCP] Connected to MCP server successfully.");
        await logToDiscord("[MCP] Grace connected to local Filesystem MCP server.");

        // Fetch tools immediately
        const toolsResponse = await mcpClient.listTools();
        if (toolsResponse && toolsResponse.tools) {
            mcpToolsCache = toolsResponse.tools.map(formatMcpToolForGemini);
            console.log(`[MCP] Discovered ${mcpToolsCache.length} tools from MCP Server.`);
            mcpToolsCache.forEach(t => console.log(`  -> ${t.name}`));
        }
    } catch (error) {
        console.error("[MCP] Initialization failed:", error);
        mcpClient = null;
    }
}

export function getMcpTools() {
    return mcpToolsCache;
}

export async function callMcpTool(name, args) {
    if (!mcpClient) {
        throw new Error("MCP Client is not initialized.");
    }

    console.log(`[MCP] Calling tool: ${name}`);
    const result = await mcpClient.callTool({
        name: name,
        arguments: args
    });

    // The MCP result content is an array of objects, usually { type: 'text', text: '...' }
    let resultText = "";
    if (result && result.content) {
        for (const block of result.content) {
            if (block.type === 'text') {
                resultText += block.text + "\n";
            }
        }
    }

    // Safety Truncation: Prevent massive file reads or directory lists from blowing up the Gemini token limit.
    // 50,000 chars is roughly 12,000 tokens. Gemini Free Tier max is 250k/min.
    if (resultText.length > 50000) {
        console.warn(`[MCP] Warning: Tool result from ${name} was too large (${resultText.length} chars). Truncating to 50k chars.`);
        resultText = resultText.substring(0, 50000) + "\n\n...[CONTENT TRUNCATED FOR LENGTH]...";
    }

    return resultText;
}

// Convert MCP tool JSON Schema to Gemini Function Declaration Schema
function formatMcpToolForGemini(mcpTool) {
    const properties = {};
    const required = mcpTool.inputSchema?.required || [];

    if (mcpTool.inputSchema && mcpTool.inputSchema.properties) {
        for (const [key, value] of Object.entries(mcpTool.inputSchema.properties)) {
            // Gemini types are uppercase: STRING, NUMBER, BOOLEAN, ARRAY, OBJECT
            let type = "STRING";
            if (value.type === "string") type = "STRING";
            else if (value.type === "number" || value.type === "integer") type = "NUMBER";
            else if (value.type === "boolean") type = "BOOLEAN";
            else if (value.type === "array") type = "ARRAY";
            else if (value.type === "object") type = "OBJECT";

            properties[key] = {
                type: type,
                description: value.description || ""
            };

            // Gemini strictly requires the 'items' field if the type is ARRAY
            if (type === "ARRAY") {
                properties[key].items = {
                    type: (value.items && value.items.type === "string") ? "STRING" : "STRING"
                };
            }
        }
    }
    return {
        name: mcpTool.name,
        description: mcpTool.description || `MCP Tool: ${mcpTool.name}`,
        parameters: {
            type: "OBJECT",
            properties: properties,
            required: required
        }
    };
}
