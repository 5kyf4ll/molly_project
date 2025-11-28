import React from "react";

export default function LogoutModal({ open, onClose, onConfirm }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">

      <div className="bg-gray-800 p-6 rounded-xl w-80 shadow-xl text-white">
        <h2 className="text-lg font-bold mb-4">Cerrar sesión</h2>
        <p className="text-gray-300 mb-6">¿Seguro que deseas cerrar sesión?</p>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-gray-600 hover:bg-gray-700"
          >
            Cancelar
          </button>

          <button
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600"
          >
            Salir
          </button>
        </div>
      </div>

    </div>
  );
}
