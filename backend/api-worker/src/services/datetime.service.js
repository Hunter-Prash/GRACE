export function getCurrentDateTime(offsetDays = 0) {
    try {
        const date = new Date();
        if (offsetDays !== 0) {
            date.setDate(date.getDate() + offsetDays);
        }

        // Convert to IST
        const istOptions = {
            timeZone: 'Asia/Kolkata',
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        };

        const formatter = new Intl.DateTimeFormat('en-IN', istOptions);
        const parts = formatter.formatToParts(date);
        
        let formattedString = "";
        parts.forEach(p => {
            formattedString += p.value;
        });

        return {
            status: "success",
            isoString: date.toISOString(),
            istFormatted: formattedString,
            offsetDaysApplied: offsetDays
        };
    } catch (err) {
        console.error("[DATETIME SERVICE ERROR]", err);
        return { status: "error", message: err.message };
    }
}
