// src/components/common/ProtectedRoute.jsx
import { useContext } from "react";
import { Navigate } from "react-router-dom";
import { AppContext } from "../../context/AppContext";

const ProtectedRoute = ({ children }) => {
    const { isAuthenticated } = useContext(AppContext);

    if (!isAuthenticated) return <Navigate to="/login" />;

    return children;
};

export default ProtectedRoute;
