import { exec } from "child_process";

console.log("Testing start...");
exec(`start "" steam://`, (error, stdout, stderr) => {
    if (error) {
        console.error("Error steam:", error.message);
    } else {
        console.log("Success steam!");
    }
});
exec(`start "" "steam://"`, (error, stdout, stderr) => {
    if (error) {
        console.error("Error quoted steam:", error.message);
    } else {
        console.log("Success quoted steam!");
    }
});
