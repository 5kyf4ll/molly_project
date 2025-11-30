// src/api/mollyApi.js

export async function loginRequest(username, password) {
  try {
    const res = await fetch("http://192.168.1.38:5000/api/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    return data.success;   // <- AHORA SI REGRESAMOS TRUE / FALSE
  } catch (e) {
    console.error("Error en login:", e);
    return false;
  }
}


export async function sendMessageToMolly(message) {
  try {
    const res = await fetch("http://192.168.1.38:5000/api/chat", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    return await res.json();
  } catch (error) {
    console.error("Error enviando mensaje a Molly:", error);
    return { error: "Error de conexion con Molly" };
  }
}
