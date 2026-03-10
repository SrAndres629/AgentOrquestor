"""
AgentOrquestor - Cryptographic Shield
=====================================
Motor de cifrado simétrico para la protección de código propietario.
Garantiza que los fragmentos de código (payloads) almacenados en ChromaDB 
estén cifrados en reposo (At-Rest Encryption).
"""

import os
from cryptography.fernet import Fernet
from typing import Union

class CryptoManager:
    """
    Gestor de cifrado basado en Fernet.
    """
    def __init__(self):
        # Intentar cargar llave desde el entorno, de lo contrario generar una para la sesión
        # NOTA: En producción 2026, AGENT_ORQUESTOR_ENC_KEY debe ser inyectada por el IDE.
        self.key = os.getenv("AGENT_ORQUESTOR_ENC_KEY", Fernet.generate_key().decode())
        self.cipher = Fernet(self.key.encode())

    def encrypt_payload(self, data: str) -> bytes:
        """Cifra un string de código y devuelve el token binario."""
        if not data: return b""
        return self.cipher.encrypt(data.encode())

    def decrypt_payload(self, token: Union[bytes, str]) -> str:
        """Descifra un token y devuelve el string original."""
        if not token: return ""
        if isinstance(token, str):
            token = token.encode()
        return self.cipher.decrypt(token).decode()

# Singleton de Seguridad
crypto = CryptoManager()
