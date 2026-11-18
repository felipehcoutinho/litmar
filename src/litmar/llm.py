"""Creación del modelo de lenguaje configurado para litmar."""

import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter

_CLAVES_POR_PROVEEDOR = {
    "google_genai": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}
_LLAMADAS_GEMINI_POR_MINUTO = 10
_LIMITADOR_GEMINI = InMemoryRateLimiter(
    requests_per_second=_LLAMADAS_GEMINI_POR_MINUTO / 60,
    check_every_n_seconds=0.1,
    max_bucket_size=1,
)


def crear_modelo() -> BaseChatModel:
    """Crea el modelo indicado en LITMAR_MODELO, validando la clave del proveedor."""
    configuracion = os.getenv("LITMAR_MODELO", "").strip()
    if not configuracion:
        raise ValueError("Falta LITMAR_MODELO. Añade LITMAR_MODELO=proveedor:modelo al .env.")

    proveedor, separador, nombre = configuracion.partition(":")
    proveedor = proveedor.strip()
    nombre = nombre.strip()
    if not separador or not proveedor or not nombre:
        raise ValueError("LITMAR_MODELO debe tener el formato proveedor:modelo.")
    configuracion = f"{proveedor}:{nombre}"

    clave = _CLAVES_POR_PROVEEDOR.get(proveedor)
    if clave is None:
        proveedores = " o ".join(_CLAVES_POR_PROVEEDOR)
        raise ValueError(f"Proveedor no admitido en LITMAR_MODELO. Usa {proveedores}.")
    if not os.getenv(clave, "").strip():
        raise ValueError(f"Falta {clave}. Añade al .env: {clave}=tu_clave.")

    if proveedor == "google_genai":
        return init_chat_model(model=configuracion, rate_limiter=_LIMITADOR_GEMINI)
    return init_chat_model(model=configuracion)
