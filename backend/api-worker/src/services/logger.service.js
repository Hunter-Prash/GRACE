import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config();

const webhookUrl = process.env.DISCORD_WEBHOOK_URL;

export const logToDiscord = async (message, isImportant = false) => {
    // We also want to log it to the standard console
    if (isImportant) {
        console.log(`\x1b[36m${message}\x1b[0m`); // Cyan for important console logs
    } else {
        console.log(message);
    }

    if (!webhookUrl) {
        return;
    }

    try {
        // Formatting for Discord
        const formattedMessage = isImportant ? `**${message}**` : `\`${message}\``;
        
        await axios.post(webhookUrl, {
            content: formattedMessage
        });
    } catch (e) {
        // Don't throw an error and crash the app just because logging failed
        console.error("[Logger] Failed to push log to Discord:", e.message);
    }
};
