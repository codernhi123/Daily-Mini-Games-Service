import axios from 'axios';

export const api = axios.create({
    // baseURL: "http://localhost:8000",
    baseURL: "https://user-service-lxv0.onrender.com",
    headers: {
        'Content-Type': 'application/json'
    },
    withCredentials: true
});