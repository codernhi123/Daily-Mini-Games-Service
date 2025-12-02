import axios from 'axios';

export const api = axios.create({
    // baseURL: "http://localhost:8000",
    baseURL: import.meta.env.VITE_BACKEND_URL,
    headers: {
        'Content-Type': 'application/json'
    },
    withCredentials: true
});