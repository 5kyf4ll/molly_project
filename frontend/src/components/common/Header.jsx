// src/components/common/Header.jsx
import React from "react";
import { Settings } from "lucide-react";

export default function Header({ title = "Molly Dashboard" }) {
  return (
    <header className="relative flex items-center p-4 bg-gray-800 shadow-xl border-b border-gray-700">
      
      {/* Título centrado */}
      <h1 className="
        absolute left-1/2 transform -translate-x-1/2 
        text-2xl font-semibold text-white
      ">
        {title}
      </h1>

      {/* Avatar alineado a la derecha */}
      <div className="ml-auto w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-sm font-medium">
        A
      </div>

    </header>
  );
}


