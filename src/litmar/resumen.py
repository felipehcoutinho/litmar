"""Resumen estructurado de un artículo científico."""

from typing import Protocol

from pydantic import BaseModel, Field

from litmar.articulo import Articulo


class ResumenArticulo(BaseModel):
    """Resumen de un artículo orientado a una pregunta de investigación."""

    objetivo: str = Field(description="Objetivo principal del artículo.")
    metodo: str = Field(description="Método o enfoque usado por el estudio.")
    hallazgos: str = Field(description="Resultados o hallazgos principales.")
    relevancia: int = Field(
        ge=1,
        le=5,
        description="Relevancia del artículo para la pregunta, de 1 (baja) a 5 (alta).",
    )
    limitaciones: str = Field(description="Limitaciones indicadas o evidentes en el resumen.")


class _SalidaEstructurada(Protocol):
    def invoke(self, input: str) -> object: ...


class ModeloEstructurado(Protocol):
    def with_structured_output(self, schema: type[ResumenArticulo]) -> _SalidaEstructurada: ...


def resumir(articulo: Articulo, pregunta: str, modelo: ModeloEstructurado) -> ResumenArticulo:
    """Resume el artículo según la pregunta usando la salida estructurada del modelo."""
    if not articulo.abstract.strip():
        raise ValueError("No se puede resumir un artículo sin resumen.")

    prompt = (
        "Responde en español y usa únicamente la información del artículo. "
        "No inventes datos que no aparezcan en el resumen.\n\n"
        f"Pregunta de investigación: {pregunta}\n"
        f"Título: {articulo.title}\n"
        f"Año: {articulo.year}\n"
        f"Autores: {'; '.join(articulo.authors)}\n"
        f"DOI: {articulo.doi}\n"
        f"Resumen del artículo:\n{articulo.abstract}"
    )
    resultado = modelo.with_structured_output(ResumenArticulo).invoke(prompt)
    if not isinstance(resultado, ResumenArticulo):
        raise TypeError("El modelo no devolvió un objeto ResumenArticulo.")
    return resultado
