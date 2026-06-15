import axios from 'axios';
import dotenv from 'dotenv';
dotenv.config({ path: '../.env' });

async function run() {
    const key = process.env.TOMTOM_API_KEY;
    try {
        const res = await axios.get(`https://api.tomtom.com/routing/1/calculateRoute/12.8422,80.2223:12.8234,80.2120/json?key=${key}`);
        console.log(Object.keys(res.data));
    } catch (e) {
        console.error(e.response ? e.response.data : e.message);
    }
}
run();
