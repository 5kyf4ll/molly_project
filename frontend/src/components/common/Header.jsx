// src/components/common/Header.jsx
import React from "react";
import { Settings } from "lucide-react";

export default function Header({ title = "Molly Dashboard" }) {
  return (
    <header className="flex items-center justify-between p-4 bg-gray-800 shadow-xl border-b border-gray-700">
      <h1 className="text-2xl font-semibold text-white">
        {title}
      </h1>

      <div className="flex items-center space-x-4">
        <button className="text-gray-400 hover:text-white transition-colors p-2 rounded-full hover:bg-gray-700">
          <Settings className="w-5 h-5" />
        </button>

        <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-medium">
          L
        </div>
      </div>
    </header>
  );
}
