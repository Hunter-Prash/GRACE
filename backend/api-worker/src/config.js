import fs from 'fs';
import path from 'path';
import yaml from 'yaml';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const configPath = path.resolve(__dirname, '../../config.yaml');

let config = {};
try {
    const file = fs.readFileSync(configPath, 'utf8');
    config = yaml.parse(file);
} catch (e) {
    console.warn("Could not load config.yaml. Using environment variables instead.");
}

export const getGeminiKey = () => config.GEMINI_API_KEY || process.env.GEMINI_API_KEY;
export const getAwsRegion = () => process.env.AWS_REGION || 'ap-south-1';
