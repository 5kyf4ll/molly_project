// src/context/AppContext.jsx
import { createContext, useState } from "react";

export const AppContext = createContext();

export function AppProvider({ children }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [user, setUser] = useState(null);

    const login = (username) => {
        setIsAuthenticated(true);
        setUser({ username });
    };

    const logout = () => {
        setIsAuthenticated(false);
        setUser(null);
    };

    return (
        <AppContext.Provider value={{ isAuthenticated, user, login, logout }}>
            {children}
        </AppContext.Provider>
    );
}
