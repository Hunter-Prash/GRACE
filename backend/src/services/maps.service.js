import axios from 'axios';
import dotenv from 'dotenv';

// Load .env so process.env works locally when testing
dotenv.config();

// Helper function to convert text addresses into GPS coordinates for TomTom Routing
const getCoordinates = async (address) => {
    // If the LLM already passed raw coordinates, bypass geocoding
    if (/^-?\d+(\.\d+)?,-?\d+(\.\d+)?$/.test(address.replace(/\s/g, ''))) {
        return address.replace(/\s/g, '');
    }

    try {
        const url = `https://api.tomtom.com/search/2/geocode/${encodeURIComponent(address)}.json?key=${process.env.TOMTOM_API_KEY}`;
        const response = await axios.get(url);
        if (response.data.results && response.data.results.length > 0) {
            const pos = response.data.results[0].position;
            return `${pos.lat},${pos.lon}`; // TomTom Routing requires lat,lon format
        }
        return null;
    } catch (e) {
        console.error(`[MAPS] Geocode Error for ${address}:`, e.message);
        return null;
    }
};

export const getCommuteTime = async (origin, destination) => {
    try {
        // 1. Convert "HITEC City" to exact GPS coordinates
        const originCoords = await getCoordinates(origin);
        const destCoords = await getCoordinates(destination);

        if (!originCoords || !destCoords) {
            console.log("[MAPS] Could not geocode addresses.");
            return null;
        }

        // 2. Query TomTom Routing API with live traffic enabled
        const url = `https://api.tomtom.com/routing/1/calculateRoute/${originCoords}:${destCoords}/json?traffic=true&key=${process.env.TOMTOM_API_KEY}`;
        const response = await axios.get(url);
        
        if (response.data.routes && response.data.routes.length > 0) {
            // TomTom returns travel time in seconds, so we format it
            const seconds = response.data.routes[0].summary.travelTimeInSeconds;
            const minutes = Math.round(seconds / 60);
            const lengthInMeters = response.data.routes[0].summary.lengthInMeters;
            const distanceKm = (lengthInMeters / 1000).toFixed(1);
            
            const eta = `${minutes} minutes (with live traffic)`;
            console.log(`[MAPS] ETA from ${origin} to ${destination}:`, eta, `| Distance: ${distanceKm} km`);
            return {
                eta: eta,
                distance: `${distanceKm} km`,
                originCoords: originCoords,
                destCoords: destCoords
            };
        } else {
            console.log("[MAPS] Directions API Error or No Route.");
            return null;
        }
    } catch (e) {
        console.error("[MAPS] Routing Error:", e.message);
        return null;
    }
}

export const getNearbyPlaces = async (query) => {
    try {
        const url = `https://api.tomtom.com/search/2/poiSearch/${encodeURIComponent(query)}.json?key=${process.env.TOMTOM_API_KEY}`;
        const response = await axios.get(url);
        
        if (response.data.results && response.data.results.length > 0) {
            // Get top 3 places so we don't flood Grace's context window
            const places = response.data.results.slice(0, 3).map(p => ({
                name: p.poi.name,
                address: p.address.freeformAddress,
                category: p.poi.classifications ? p.poi.classifications[0].code : "Unknown",
                coords: `${p.position.lat},${p.position.lon}`
            }));
            console.log(`[MAPS] Top results for "${query}":`, places);
            return places;
        } else {
            console.log("[MAPS] Places API Error or No Results.");
            return [];
        }
    } catch (e) {
        console.error("[MAPS] Places Error:", e.message);
        return [];
    }
}

// ---- LOCAL TESTING ----
// Uncomment the lines below to test it manually, but comment them out before starting Grace!

// await getNearbyPlaces('best cafes near Hyderabad');
// await getCommuteTime('HITEC City, Hyderabad', 'Charminar, Hyderabad');