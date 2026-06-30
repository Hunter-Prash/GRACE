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

        // Generate an exact ISO string with +05:30 offset
        const pad = (n) => n < 10 ? '0' + n : n;
        const istDateObj = new Date(date.getTime() + (5.5 * 60 * 60 * 1000));
        const istIsoString = istDateObj.getUTCFullYear() +
            '-' + pad(istDateObj.getUTCMonth() + 1) +
            '-' + pad(istDateObj.getUTCDate()) +
            'T' + pad(istDateObj.getUTCHours()) +
            ':' + pad(istDateObj.getUTCMinutes()) +
            ':' + pad(istDateObj.getUTCSeconds()) +
            '+05:30';

        return {
            status: "success",
            isoString: date.toISOString(), // Raw UTC ISO
            istIsoString: istIsoString, // Formatted IST ISO
            istFormatted: formattedString,
            offsetDaysApplied: offsetDays
        };
    } catch (err) {
        console.error("[DATETIME SERVICE ERROR]", err);
        return { status: "error", message: err.message };
    }
}
