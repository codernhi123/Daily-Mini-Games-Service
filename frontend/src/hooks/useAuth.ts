import { useState, useEffect } from "react";

interface User {
    id: number;
    name: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await fetch("https://user-service-lxv0.onrender.com/v2/authentications/me", {
          method: "GET",
          credentials: "include"
        });

        if (!res.ok) {
          setUser(null);
          return;
        }

        const data = await res.json();
        setUser(data); // {id, name}
      } catch (error) {
        console.error("Failed to fetch user", error);
        setUser(null);
      }
    };

    fetchUser();
  }, []);

  return { user, setUser };
}