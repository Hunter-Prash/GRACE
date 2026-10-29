import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { handler } from './src/cron.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.resolve(__dirname, '../.env') });
dotenv.config({ path: path.resolve(__dirname, '../../config.yaml') });

const target = (process.argv[2] || 'motivation').toLowerCase();

const actionMap = {
    motivation: 'triggerMotivation',
    calendar: 'triggerCalendar',
    braindump: 'triggerBrainDump',
    goals: 'triggerGoalAnalyzer',
    strategy: 'triggerWeeklyStrategy',
    all: 'triggerAll'
};

const action = actionMap[target] || target;

console.log(`\n========================================================`);
console.log(`TESTING CRON JOB: ${target.toUpperCase()} (Action: ${action})`);
console.log(`========================================================\n`);

handler({ action })
    .then(res => {
        console.log("\n========================================================");
        console.log("CRON RESULT:", res);
        console.log("========================================================\n");
        process.exit(0);
    })
    .catch(err => {
        console.error("\nCRON EXECUTION ERROR:", err);
        process.exit(1);
    });

