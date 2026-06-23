import re

with open('d:/PERSONAL/GRACE/backend/api-worker/src/services/llm.service.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add tool definition
tool_def = '''            {
                name: "detectFileOperation",
                description: "Triggers the scene_mode context panel in the GUI to show a directory preview. Call this when you perform or detect a file creation, modification, or deletion.",
                parameters: {
                    type: "OBJECT",
                    properties: {
                        directory: { type: "STRING", description: "The path of the directory" },
                        file_changed: { type: "STRING", description: "The name of the file created or modified" },
                        free_space: { type: "STRING", description: "Free space remaining (e.g. '1.2 TB' or 'UNKNOWN')" },
                        last_backup: { type: "STRING", description: "Last backup timestamp (e.g. '2023-10-01' or 'UNKNOWN')" }
                    },
                    required: ["directory", "file_changed", "free_space", "last_backup"]
                }
            },
            {
                name: "getCurrentDateTime",'''

content = content.replace('            {\n                name: "getCurrentDateTime",', tool_def)

# Add handler
handler_code = '''                else if (call.name === 'getCurrentDateTime') {
                    const args = call.args || {};
                    const res = getCurrentDateTime(args.offsetDays || 0);
                    toolResult = { success: true, datetime: res };
                }
                else if (call.name === 'detectFileOperation') {
                    const args = call.args;
                    clientCommands.push({ type: 'fileOperation', data: args });
                    toolResult = { success: true, message: `Triggered file operation UI context for ${args.file_changed}` };
                }'''

content = content.replace("""                else if (call.name === 'getCurrentDateTime') {
                    const args = call.args || {};
                    const res = getCurrentDateTime(args.offsetDays || 0);
                    toolResult = { success: true, datetime: res };
                }""", handler_code)

with open('d:/PERSONAL/GRACE/backend/api-worker/src/services/llm.service.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done modifying llm.service.js')
