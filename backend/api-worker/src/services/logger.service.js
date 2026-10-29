import axios from 'axios';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../../../.env') });

export const logToDiscord = async (message, isImportant = false) => {
    // We also want to log it to the standard console
    if (isImportant) {
        console.log(`\x1b[36m${message}\x1b[0m`); // Cyan for important console logs
    } else {
        console.log(message);
    }

    const webhookUrl = process.env.DISCORD_WEBHOOK_URL;
    if (!webhookUrl) {
        return;
    }

    try {
        const rawText = String(message);
        // If content is within Discord's 2000 character limit, send directly
        if (rawText.length <= 1900) {
            await axios.post(webhookUrl, { content: rawText });
            return;
        }

        // Chunk into <= 1900 chars respecting newlines so long reviews deliver cleanly
        let remaining = rawText;
        while (remaining.length > 0) {
            let chunk = remaining.slice(0, 1900);
            if (remaining.length > 1900) {
                const lastNewline = chunk.lastIndexOf('\n');
                if (lastNewline > 500) {
                    chunk = remaining.slice(0, lastNewline);
                }
            }
            remaining = remaining.slice(chunk.length).trim();
            await axios.post(webhookUrl, { content: chunk });
            if (remaining.length > 0) {
                await new Promise(r => setTimeout(r, 300)); // prevent Discord rate-limiting
            }
        }
    } catch (e) {
        // Don't throw an error and crash the app just because logging failed
        console.error("[Logger] Failed to push log to Discord:", e.message);
    }
};
