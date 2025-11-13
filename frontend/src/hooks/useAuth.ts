import { useState, useEffect } from "react";

interface User {
    id: number;
    name: string;
}

export function useAuth() {
    const [user, setUser] = useState<User | null>(null);
    useEffect(() => {
        const storedUser = localStorage.getItem('user')
        if (storedUser) {
            setUser(JSON.parse(storedUser));
        }
    }, []);
    return { user, setUser}
}