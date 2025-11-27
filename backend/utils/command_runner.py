# src/utils/command_runner.py
import subprocess
import shlex 
import os
import time
from typing import Optional # ¡Esta es la línea que faltaba!

class CommandResult:
    """
    Clase para encapsular el resultado de la ejecución de un comando.
    """
    def __init__(self, command: str, success: bool, stdout: str, stderr: str, returncode: int, duration: float):
        self.command = command
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.duration = duration

    def __str__(self):
        status = "Éxito" if self.success else "Fallo"
        return (f"Comando: {self.command}\n"
                f"Estado: {status} (Código de retorno: {self.returncode})\n"
                f"Duración: {self.duration:.2f}s\n"
                f"STDOUT:\n{self.stdout}\n"
                f"STDERR:\n{self.stderr}")

class CommandRunner:
    """
    Proporciona un método seguro y robusto para ejecutar comandos del sistema.
    """
    def __init__(self, timeout: int = 300):
        self.default_timeout = timeout
        print(f"[CommandRunner] Inicializado con timeout por defecto: {self.default_timeout}s")

    def run_command(self, command: str, timeout: Optional[int] = None) -> CommandResult:
        """
        Ejecuta un comando del sistema de forma segura.
        Args:
            command (str): El comando a ejecutar (ej. "nmap -sV 127.0.0.1").
            timeout (Optional[int]): Tiempo máximo en segundos para la ejecución del comando.
                                     Si es None, usa el timeout por defecto del inicializador.

        Returns:
            CommandResult: Un objeto que contiene el resultado de la ejecución.
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout
        start_time = time.time()
        
        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                check=False
            )
            
            end_time = time.time()
            duration = end_time - start_time

            success = process.returncode == 0

            return CommandResult(
                command=command,
                success=success,
                stdout=process.stdout,
                stderr=process.stderr,
                returncode=process.returncode,
                duration=duration
            )
        except subprocess.TimeoutExpired:
            end_time = time.time()
            duration = end_time - start_time
            print(f"[CommandRunner ERROR] Comando '{command}' excedió el tiempo límite de {effective_timeout}s.")
            return CommandResult(
                command=command,
                success=False,
                stdout="",
                stderr=f"Comando excedió el tiempo límite ({effective_timeout}s).",
                returncode=-1,
                duration=duration
            )
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"[CommandRunner ERROR] Error inesperado al ejecutar comando '{command}': {e}")
            return CommandResult(
                command=command,
                success=False,
                stdout="",
                stderr=f"Error inesperado: {e}",
                returncode=-2,
                duration=duration
            )

# Ejemplo de uso (para pruebas rápidas)
if __name__ == '__main__':
    runner = CommandRunner()

    print("\n--- Probando un comando exitoso ---")
    result = runner.run_command("echo Hola Molly!")
    print(result)

    print("\n--- Probando un comando fallido (comando no existe) ---")
    result = runner.run_command("thiscommanddoesnotexist")
    print(result)

    print("\n--- Probando un comando con timeout (solo en Linux/macOS para 'sleep') ---")
    result = runner.run_command("sleep 5 && echo Desperté", timeout=2)
    print(result)

    print("\n--- Probando un comando con salida a stderr ---")
    result = runner.run_command("ls non_existent_file_123")
    print(result)