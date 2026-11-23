import { CostExplorerClient, GetCostAndUsageCommand } from '@aws-sdk/client-cost-explorer';
import { saveBrainDump, getBrainDumpNotes, updateBrainDumpStatus } from './braindump.service.js';
import { addTransaction } from './finance.service.js';

// Cost Explorer API endpoint operates in us-east-1 globally
const ceClient = new CostExplorerClient({ region: 'us-east-1' });

// Realistic USD to INR conversion baseline
const USD_TO_INR_RATE = 85.0;

function formatInr(usd) {
    return Math.round(usd * USD_TO_INR_RATE);
}

/**
 * Low-level query to AWS Cost Explorer
 */
export async function getAwsCostAndUsage(startDate, endDate) {
    try {
        const cmd = new GetCostAndUsageCommand({
            TimePeriod: { Start: startDate, End: endDate },
            Granularity: 'MONTHLY',
            Metrics: ['UnblendedCost']
        });

        const response = await ceClient.send(cmd);
        const results = response.ResultsByTime || [];
        if (results.length === 0) {
            return { amountUsd: 0, amountInr: 0, isEstimated: false };
        }

        const total = results[0].Total?.UnblendedCost;
        const amountUsd = parseFloat(total?.Amount || 0);
        return {
            amountUsd: Math.round(amountUsd * 100) / 100,
            amountInr: formatInr(amountUsd),
            isEstimated: results[0].Estimated || false,
            startDate,
            endDate
        };
    } catch (e) {
        console.error(`[AWS Cost] Error fetching Cost Explorer metrics (${startDate} to ${endDate}):`, e.message);
        throw e;
    }
}

/**
 * Returns previous month's finalized billing total
 */
export async function getLastMonthBill() {
    const now = new Date();
    // 1st of current month
    const currentMonthFirst = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
    // 1st of previous month
    const prevMonthFirst = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1));

    const startDate = prevMonthFirst.toISOString().split('T')[0];
    const endDate = currentMonthFirst.toISOString().split('T')[0];

    const monthLabel = prevMonthFirst.toLocaleString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' });
    const monthTag = `aws-bill-${prevMonthFirst.getUTCFullYear()}-${String(prevMonthFirst.getUTCMonth() + 1).padStart(2, '0')}`;

    const cost = await getAwsCostAndUsage(startDate, endDate);
    return {
        month: monthLabel,
        monthTag: monthTag,
        amountUsd: cost.amountUsd,
        amountInr: cost.amountInr,
        startDate,
        endDate
    };
}

/**
 * Returns current month-to-date running spend
 */
export async function getMonthToDateSpend() {
    const now = new Date();
    const currentMonthFirst = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
    // Cost Explorer requires end date to be after start date
    const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);

    const startDate = currentMonthFirst.toISOString().split('T')[0];
    const endDate = tomorrow.toISOString().split('T')[0];

    const monthLabel = now.toLocaleString('en-US', { month: 'long', year: 'numeric', timeZone: 'Asia/Kolkata' });
    const cost = await getAwsCostAndUsage(startDate, endDate);

    return {
        month: `${monthLabel} (Month-to-Date)`,
        amountUsd: cost.amountUsd,
        amountInr: cost.amountInr,
        daysElapsed: now.getDate(),
        startDate,
        endDate
    };
}

/**
 * Checks for unpaid AWS bill and records a persistent reminder note in Grace_BrainDump
 * Runs silently on the 3rd and 4th of each month.
 */
export async function syncMonthlyAwsBillToBrainDump() {
    try {
        const lastMonth = await getLastMonthBill();
        console.log(`[AWS Cost] Syncing bill for ${lastMonth.month}: $${lastMonth.amountUsd} (~₹${lastMonth.amountInr})`);

        // Check if an active or completed note for this month's bill already exists
        const activeNotes = await getBrainDumpNotes("Active", "Admin", 30);
        const existingActive = activeNotes.find(n => 
            Array.isArray(n.Tags) && (n.Tags.includes(lastMonth.monthTag) || n.Tags.includes("aws-bill"))
        );

        if (existingActive) {
            console.log(`[AWS Cost] Bill reminder already active: "${existingActive.Content}"`);
            return { synced: false, message: "Bill reminder already active", note: existingActive };
        }

        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const dueDate = `${year}-${month}-04`;

        const content = `Pay AWS Cloud bill for ${lastMonth.month}: $${lastMonth.amountUsd.toFixed(2)} (~₹${lastMonth.amountInr}).`;
        const res = await saveBrainDump(
            content,
            "Admin",
            dueDate,
            ["aws-bill", lastMonth.monthTag]
        );

        console.log(`[AWS Cost] Created bill reminder in BrainDump: "${content}"`);
        return { synced: true, bill: lastMonth, note: res.note };
    } catch (e) {
        console.error(`[AWS Cost] Failed to sync AWS bill to BrainDump: ${e.message}`);
        return { synced: false, error: e.message };
    }
}

/**
 * Checks month-to-date spend on 10th and 20th.
 * If spend exceeds threshold (default $10), logs a warning note to BrainDump.
 */
export async function checkMidMonthCostAnomaly(thresholdUsd = 10.0) {
    try {
        const mtd = await getMonthToDateSpend();
        console.log(`[AWS Cost] Mid-month check: $${mtd.amountUsd} (Threshold: $${thresholdUsd})`);

        if (mtd.amountUsd > thresholdUsd) {
            const warningContent = `AWS Cost Anomaly: Month-to-date spend reached $${mtd.amountUsd.toFixed(2)} (~₹${mtd.amountInr}), exceeding $${thresholdUsd} budget.`;
            await saveBrainDump(warningContent, "Admin", null, ["aws-cost-alert"]);
            return { anomaly: true, mtd };
        }

        return { anomaly: false, mtd };
    } catch (e) {
        console.error(`[AWS Cost] Anomaly check failed: ${e.message}`);
        return { anomaly: false, error: e.message };
    }
}

/**
 * Marks pending AWS bill as paid:
 * 1. Flips the BrainDump reminder note from Active -> Completed
 * 2. Logs the expense into Expense-Tracker-Transactions-Table
 */
export async function markAwsBillAsPaid() {
    try {
        const activeNotes = await getBrainDumpNotes("Active", "Admin", 30);
        const billNote = activeNotes.find(n => 
            Array.isArray(n.Tags) && n.Tags.includes("aws-bill")
        );

        let amountInr = 350; // fallback if cannot parse
        let noteContent = "AWS Cloud Bill";

        if (billNote) {
            noteContent = billNote.Content;
            // Parse INR from content if present, e.g. "~₹350"
            const inrMatch = billNote.Content.match(/₹(\d+)/);
            if (inrMatch) {
                amountInr = parseInt(inrMatch[1], 10);
            }
            await updateBrainDumpStatus(billNote.CreatedAt, "Completed");
            console.log(`[AWS Cost] Marked bill note as Completed: "${billNote.Content}"`);
        } else {
            // If no active note, fetch last month's bill amount
            try {
                const lastBill = await getLastMonthBill();
                amountInr = lastBill.amountInr > 0 ? lastBill.amountInr : 350;
            } catch {
                // Keep fallback
            }
        }

        // Record in financial transactions table under "career" category
        await addTransaction(amountInr, "career", noteContent);
        console.log(`[AWS Cost] Recorded ₹${amountInr} transaction in Expense-Tracker-Transactions-Table`);

        return {
            success: true,
            amountInr: amountInr,
            message: `AWS bill marked as paid. Completed the reminder note and logged ₹${amountInr} under career expenses in your finance tracker.`
        };
    } catch (e) {
        console.error(`[AWS Cost] Failed to mark bill as paid: ${e.message}`);
        throw e;
    }
}

// Alias for tool invocation
export const markAwsBillPaid = markAwsBillAsPaid;

/**
 * Comprehensive cost report for conversational use
 */
export async function getAwsCostReport() {
    const [lastMonth, mtd, activeNotes] = await Promise.all([
        getLastMonthBill().catch(err => ({ error: err.message })),
        getMonthToDateSpend().catch(err => ({ error: err.message })),
        getBrainDumpNotes("Active", "Admin", 30).catch(() => [])
    ]);

    const pendingBillNote = activeNotes.find(n => 
        Array.isArray(n.Tags) && n.Tags.includes("aws-bill")
    );

    return {
        previousMonthBill: lastMonth,
        monthToDateSpend: mtd,
        paymentStatus: pendingBillNote ? "UNPAID (Pending Payment)" : "PAID (No pending bill)",
        pendingBillReminder: pendingBillNote ? {
            content: pendingBillNote.Content,
            dueDate: pendingBillNote.DueDate,
            createdAt: pendingBillNote.CreatedAt
        } : null
    };
}
