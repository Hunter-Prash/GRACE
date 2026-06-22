const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const testDir = __dirname;
const files = fs.readdirSync(testDir);

files.forEach(file => {
    if (file.startsWith('test-') && file.endsWith('.js')) {
        console.log(`Running: ${file}...`);
        try {
            execSync(`node ${path.join(testDir, file)}`, { stdio: 'inherit' });
        } catch (error) {
            console.error(`Failed: ${file}`);
        }
    }
});
