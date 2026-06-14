import axios from 'axios';
import dotenv from 'dotenv';
import { getCommuteTime } from './src/services/maps.service.js';
dotenv.config();

async function run() {
    const origin = 'Srinivasan Nagar, 603103';
    const dest = 'TCS Siruseri';
    const res = await getCommuteTime(origin, dest);
    console.log(res);
}
run();
