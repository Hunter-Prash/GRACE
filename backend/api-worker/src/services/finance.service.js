import { QueryCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import { docClient } from './db.client.js';
import crypto from 'crypto';

const TABLE_NAME = "Expense-Tracker-Transactions-Table";
const USER_ID = "d3de2293-409d-415f-8b59-0b3ac6cd31b5";

export const ALLOWED_CATEGORIES = [
    "essentials", "entertainment", "transport", "career", "income"
];

export async function getTransactions(startDate, endDate) {
    const params = {
        TableName: TABLE_NAME,
        KeyConditionExpression: "user_id = :uid AND transaction_date BETWEEN :start AND :end",
        ExpressionAttributeValues: {
            ":uid": USER_ID,
            ":start": startDate,
            ":end": endDate
        }
    };
    try {
        const response = await docClient.send(new QueryCommand(params));
        return response.Items;
    } catch (error) {
        console.error("Error fetching transactions:", error);
        throw error;
    }
}

export async function addTransaction(amount, categoryName, description) {
    const catName = categoryName.toLowerCase();
    if (!ALLOWED_CATEGORIES.includes(catName)) {
        throw new Error(`Invalid category: ${categoryName}. Must be one of: ${ALLOWED_CATEGORIES.join(', ')}`);
    }

    const transactionId = crypto.randomUUID();
    const timestamp = new Date(new Date().getTime() + 5.5 * 60 * 60 * 1000).toISOString().replace('Z', '+05:30');

    const params = {
        TableName: TABLE_NAME,
        Item: {
            user_id: USER_ID,
            transaction_date: timestamp,
            id: transactionId,
            amount: parseFloat(amount),
            category_name: catName,
            created_at: timestamp,
            description: description || ""
        }
    };

    try {
        await docClient.send(new PutCommand(params));
        return {
            id: transactionId,
            message: "Transaction added successfully."
        };
    } catch (error) {
        console.error("Error adding transaction:", error);
        throw error;
    }
}

/**
 * Evaluates whether an impulse purchase or discretionary expense is "worth it".
 * Calculates exact hours and workdays of engineering at TCS needed to pay for the item,
 * audits current month's spending, and recommends a cooling-off waiting period.
 */
export async function evaluateImpulseSpend(itemName, amount, categoryName = "entertainment", customMonthlySalary = null) {
    const cost = parseFloat(amount);
    if (isNaN(cost) || cost <= 0) {
        throw new Error("Invalid purchase amount. Amount must be a positive number.");
    }

    const catName = (categoryName || "entertainment").toLowerCase();

    // 1. Calculate hourly & workday conversion based on net salary
    // Baseline for Software Engineer at TCS: ~₹65,000 net/month, 160 working hours/month
    const monthlyNetSalary = customMonthlySalary 
        ? parseFloat(customMonthlySalary) 
        : (parseFloat(process.env.MONTHLY_NET_INCOME) || 65000);
    const hourlyWage = Math.round(monthlyNetSalary / 160); // ~₹406 / hr
    const hoursNeeded = Math.round((cost / hourlyWage) * 10) / 10;
    const workDaysNeeded = Math.round((hoursNeeded / 8) * 10) / 10;

    // 2. Audit current month's transactions
    let monthTotalSpent = 0;
    let monthCategorySpent = 0;
    let transactionCount = 0;

    try {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const startDate = `${year}-${month}-01T00:00:00+05:30`;
        const endDate = `${year}-${month}-31T23:59:59+05:30`;

        const transactions = await getTransactions(startDate, endDate);
        if (Array.isArray(transactions)) {
            transactionCount = transactions.length;
            for (const tx of transactions) {
                const txAmount = parseFloat(tx.amount) || 0;
                monthTotalSpent += txAmount;
                if ((tx.category_name || '').toLowerCase() === catName) {
                    monthCategorySpent += txAmount;
                }
            }
        }
    } catch (e) {
        console.warn(`[Finance] Could not fetch current month transactions for audit: ${e.message}`);
    }

    // Baseline monthly discretionary entertainment budget
    const monthlyDiscretionaryBudget = parseFloat(process.env.MONTHLY_DISCRETIONARY_BUDGET) || 12000;
    const projectedCategoryTotal = monthCategorySpent + cost;
    const percentOfDiscretionaryBudget = Math.round((cost / monthlyDiscretionaryBudget) * 100);

    // 3. Determine Cooling-off Period & Impact
    let cooldownDays = 1;
    let verdict = "LOW_IMPACT_SPEND";
    let urgencyLevel = "Low";

    if (cost >= 5000 || hoursNeeded >= 12) {
        cooldownDays = 7;
        verdict = "HIGH_IMPACT_SPEND";
        urgencyLevel = "High";
    } else if (cost >= 1500 || hoursNeeded >= 4) {
        cooldownDays = 2;
        verdict = "MODERATE_IMPACT_SPEND";
        urgencyLevel = "Moderate";
    }

    const cooldownDate = new Date(Date.now() + cooldownDays * 24 * 60 * 60 * 1000);
    const cooldownDateStr = cooldownDate.toLocaleDateString('en-US', {
        timeZone: 'Asia/Kolkata',
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });

    return {
        itemName: itemName || "Unspecified Item",
        cost: cost,
        category: catName,
        hourlyWageEquivalent: hourlyWage,
        hoursOfLaborRequired: hoursNeeded,
        workDaysEquivalent: workDaysNeeded,
        monthlyNetSalaryBaseline: monthlyNetSalary,
        currentMonthCategorySpent: monthCategorySpent,
        projectedCategorySpend: projectedCategoryTotal,
        percentOfDiscretionaryBudget: percentOfDiscretionaryBudget,
        discretionaryBudgetBaseline: monthlyDiscretionaryBudget,
        recordedTransactionsThisMonth: transactionCount,
        verdict: verdict,
        urgencyLevel: urgencyLevel,
        coolingOffDaysRecommended: cooldownDays,
        coolingOffUntilDate: cooldownDateStr,
        realityCheckHeadline: `₹${cost.toLocaleString('en-IN')} represents ${hoursNeeded} hours (${workDaysNeeded} workdays) of engineering labor at TCS.`,
        recommendation: `Wait ${cooldownDays} day${cooldownDays > 1 ? 's' : ''} (until ${cooldownDateStr}). If you still genuinely want ${itemName} then, budget it for next month without guilt.`
    };
}
