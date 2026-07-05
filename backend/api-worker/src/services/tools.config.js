export const BASE_TOOLS = [{
    functionDeclarations: [
        {
            name: "createGoal",
            description: "Creates a new overarching project or goal for Prashant.",
            parameters: {
                type: "OBJECT",
                properties: {
                    goalId: { type: "STRING", description: "A short, dashed ID like 'learn-aws'" },
                    status: { type: "STRING", description: "Always 'Active'" },
                    category: { type: "STRING" },
                    description: { type: "STRING" },
                    milestones: { type: "OBJECT", description: "A map of milestone strings to boolean false, e.g. {'buy-book': false}" }
                },
                required: ["goalId", "category", "description", "milestones"]
            }
        },
        {
            name: "updateMilestone",
            description: "Marks a specific milestone within a goal as complete or incomplete. IMPORTANT: If you do not know the exact milestone key, use getGoalMilestones first to avoid creating duplicates.",
            parameters: {
                type: "OBJECT",
                properties: {
                    goalId: { type: "STRING" },
                    milestoneKey: { type: "STRING" },
                    isComplete: { type: "BOOLEAN" }
                },
                required: ["goalId", "milestoneKey", "isComplete"]
            }
        },
        {
            name: "updateDailyMetrics",
            description: "Logs Prashant's daily habits, mood, energy, or focus. Call this whenever he mentions completing a habit or feeling a certain way.",
            parameters: {
                type: "OBJECT",
                properties: {
                    habits: { type: "ARRAY", items: { type: "STRING" }, description: "List of habits completed today" },
                    mood_score: { type: "INTEGER", description: "Score from 1 to 10" },
                    energy_lvl: { type: "INTEGER", description: "Score from 1 to 10" },
                    core_focus: { type: "STRING" }
                }
            }
        },
        {
            name: "getAllDailyMetrics",
            description: "Fetches historical daily metrics logs. If the user asks for a specific date range (e.g. 'June' or 'last week'), provide the start and end dates in YYYY-MM-DD format. If no range is specified, do not provide these parameters.",
            parameters: {
                type: "OBJECT",
                properties: {
                    start: { type: "STRING", description: "Start date in YYYY-MM-DD format (e.g., 2026-06-01)" },
                    end: { type: "STRING", description: "End date in YYYY-MM-DD format (e.g., 2026-06-30)" }
                }
            }
        },
        {
            name: "openResource",
            description: "Opens a desktop application or a specific website on the user's computer. Call this whenever the user asks to open an app (e.g. 'chrome', 'vscode', 'spotify') or a website (e.g. 'youtube', 'google'). If it is a website, you MUST pass a fully qualified https:// URL.",
            parameters: {
                type: "OBJECT",
                properties: {
                    resourceName: { type: "STRING", description: "The exact application name, OR the full https:// URL to open." }
                },
                required: ["resourceName"]
            }
        },
        {
            name: "getActiveGoals",
            description: "Fetches all of Prashant's currently active goals and their milestones from the database. Use this when you need to know what goals exist, what the milestone keys are, or when he asks for a status update on his goals.",
            parameters: {
                type: "OBJECT",
                properties: {} // No parameters needed
            }
        },
        {
            name: "getGoalMilestones",
            description: "Fetches all milestones for a specific goal. Use this to find the exact milestone keys before attempting to update a milestone or when asked to list milestones for a particular goal.",
            parameters: {
                type: "OBJECT",
                properties: {
                    goalId: { type: "STRING", description: "The ID of the goal" }
                },
                required: ["goalId"]
            }
        },
        {
            name: "deleteGoalOrMilestone",
            description: "Deletes an entire goal, or a specific milestone within a goal if milestoneKey is provided. Use this whenever the user asks to delete a goal or remove a milestone.",
            parameters: {
                type: "OBJECT",
                properties: {
                    goalId: { type: "STRING", description: "The ID of the goal to delete or modify" },
                    milestoneKey: { type: "STRING", description: "Optional. The specific milestone to delete. If left empty or omitted, the entire goal will be deleted." }
                },
                required: ["goalId"]
            }
        },
        {
            name: "getCommuteTime",
            description: "Gets the live ETA, drive time, and exact distance between any two locations or cities. MUST call this whenever the user asks for the distance, route, or commute time between places.",
            parameters: {
                type: "OBJECT",
                properties: {
                    origin: { type: "STRING", description: "The starting address or landmark" },
                    destination: { type: "STRING", description: "The destination address or landmark" }
                },
                required: ["origin", "destination"]
            }
        },
        {
            name: "getNearbyPlaces",
            description: "Searches for nearby places like cafes, gyms, or restaurants based on a text query.",
            parameters: {
                type: "OBJECT",
                properties: {
                    query: { type: "STRING", description: "What to search for, e.g., 'gyms near HITEC City', 'best coffee shops'" }
                },
                required: ["query"]
            }
        },
        {
            name: "searchWeb",
            description: "Performs a live web search using DuckDuckGo and returns text snippets of the top results. Use this whenever the user asks for real-time information, news, current events, factual lookups, or asks you to search the web.",
            parameters: {
                type: "OBJECT",
                properties: {
                    query: { type: "STRING", description: "The precise search query to look up on the web" }
                },
                required: ["query"]
            }
        },
        {
            name: "detectFileOperation",
            description: "Triggers the scene_mode context panel in the GUI to show a directory preview. Call this when you perform or detect ANY file operation including reading, viewing, creation, modification, or deletion.",
            parameters: {
                type: "OBJECT",
                properties: {
                    directory: { type: "STRING", description: "The FULL absolute path of the directory containing the file (e.g. 'D:/PERSONAL/GRACE/core')" },
                    file_changed: { type: "STRING", description: "Just the filename, not the full path (e.g. 'hello.txt')" },
                    operation: { type: "STRING", description: "The type of operation: 'NEW' for creation, 'MODIFIED' for edits, 'DELETE' for deletion, 'READ' for reading/viewing" }
                },
                required: ["directory", "file_changed", "operation"]
            }
        },
        {
            name: "getCurrentDateTime",
            description: "Gets the exact current date and time in IST (Indian Standard Time). Can also calculate future or past dates by providing an offset in days. Use this whenever the user asks about the current date, time, or asks questions like 'a month from now', 'few days from now', etc.",
            parameters: {
                type: "OBJECT",
                properties: {
                    offsetDays: { type: "INTEGER", description: "Optional. Number of days to add (positive) or subtract (negative) from the current date." }
                }
            }
        },
        {
            name: "getCalendarEvents",
            description: "Fetches events from the user's Google Calendar. timeMin and timeMax must be RFC3339 timestamps using the IST offset (e.g., 2026-06-27T00:00:00+05:30). Use this when the user asks what's on their schedule or checks their availability. IMPORTANT: If fetching events for 'today' or 'upcoming', you MUST set timeMin to the EXACT current IST time provided in your system prompt (e.g., 2026-06-30T20:06:45+05:30). Do NOT use midnight of today, or you will accidentally fetch events that have already passed.",
            parameters: {
                type: "OBJECT",
                properties: {
                    timeMin: { type: "STRING", description: "Start time (RFC3339 string)" },
                    timeMax: { type: "STRING", description: "End time (RFC3339 string)" }
                },
                required: ["timeMin", "timeMax"]
            }
        },
        {
            name: "scheduleEvent",
            description: "Schedules a new event in the user's Google Calendar. Timestamps must be RFC3339 format. Provide the EXACT local time requested and simply append +05:30. DO NOT subtract 5.5 hours. Example: 4:00 PM IST must be exactly T16:00:00+05:30.",
            parameters: {
                type: "OBJECT",
                properties: {
                    summary: { type: "STRING", description: "Title of the event" },
                    startTime: { type: "STRING", description: "Start time (RFC3339 string)" },
                    endTime: { type: "STRING", description: "End time (RFC3339 string)" },
                    description: { type: "STRING", description: "Optional description or context for the event" },
                    recurrence: { type: "ARRAY", items: { type: "STRING" }, description: "Optional recurrence rule, e.g., ['RRULE:FREQ=YEARLY']" }
                },
                required: ["summary", "startTime", "endTime"]
            }
        },
        {
            name: "rescheduleEvent",
            description: "Moves an existing calendar event to a new time. Timestamps must be RFC3339 format. Provide the EXACT local time requested and simply append +05:30. DO NOT subtract 5.5 hours.",
            parameters: {
                type: "OBJECT",
                properties: {
                    eventId: { type: "STRING", description: "The ID of the event to reschedule" },
                    newStartTime: { type: "STRING", description: "New start time (RFC3339 string)" },
                    newEndTime: { type: "STRING", description: "New end time (RFC3339 string)" }
                },
                required: ["eventId", "newStartTime", "newEndTime"]
            }
        },
        {
            name: "cancelEvent",
            description: "Cancels/deletes an event from the user's Google Calendar.",
            parameters: {
                type: "OBJECT",
                properties: {
                    eventId: { type: "STRING", description: "The ID of the event to cancel" }
                },
                required: ["eventId"]
            }
        },
        {
            name: "getTransactions",
            description: "Fetches user's transactions from their finance database between two dates. Useful for finance insights, tracking spending, etc.",
            parameters: {
                type: "OBJECT",
                properties: {
                    startDate: { type: "STRING", description: "Start date in ISO format, e.g., 2026-06-01T00:00:00+05:30" },
                    endDate: { type: "STRING", description: "End date in ISO format, e.g., 2026-06-30T23:59:59+05:30" }
                },
                required: ["startDate", "endDate"]
            }
        },
        {
            name: "addTransaction",
            description: `Logs a new expense transaction to the database. ONLY use the following categories: essentials, entertainment, transport, career, income.`,
            parameters: {
                type: "OBJECT",
                properties: {
                    amount: { type: "NUMBER", description: "The cost of the transaction" },
                    categoryName: { type: "STRING", description: "Must be strictly one of: essentials, entertainment, transport, career, income" },
                    description: { type: "STRING", description: "A brief description of what was bought" },
                    dateIsoString: { type: "STRING", description: "Optional. Date in ISO format. If omitted, uses current time." }
                },
                required: ["amount", "categoryName", "description"]
            }
        }
    ]
}];
