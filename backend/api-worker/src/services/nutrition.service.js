import { getTodaysWorkout } from './workout.service.js';

/**
 * Gathers live biometric & lifestyle context for Gemini to dynamically formulate
 * intelligent, unscripted meal recommendations.
 */
export async function getMealContext() {
    let workedOutToday = false;
    let workoutSummary = "No workout recorded today";
    let exercises = [];

    try {
        const todayWorkout = await getTodaysWorkout();
        if (todayWorkout && todayWorkout.length > 0) {
            workedOutToday = true;
            exercises = todayWorkout.map(w => ({
                exercise: w.ExerciseName,
                sets: w.Sets ? w.Sets.length : 0
            }));
            workoutSummary = todayWorkout.map(w => w.ExerciseName).join(", ");
        }
    } catch (e) {
        // Fallback gracefully if database lookup fails
    }

    return {
        workedOutToday,
        workoutSummary,
        exercises,
        userLocation: "Siruseri, Chennai (Zolo Mirage / OMR)",
        foodEnvironment: "Access to local groceries, kitchen at PG/apartment, and Swiggy/Zomato delivery near Siruseri",
        nutritionGuidance: workedOutToday 
            ? "Trained today: Prioritize high-protein (30g+) muscle recovery and nutrient replenishment." 
            : "Rest day: Prioritize balanced nutrition, protein (~25g), and clean digestion."
    };
}
