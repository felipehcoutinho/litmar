"""API web de litmar con FastAPI: otro punto de entrada, como la CLI y la UI.

No hay lógica nueva: `/buscar` usa `buscar_en_fuentes` y `/revisiones`,
`flujo.revisar` o `agente.revisar`. Aquí solo se decide qué entra (modelos de
entrada, validados por FastAPI antes de llegar al código), qué sale (modelos de
salida, siempre con la misma forma) y qué código HTTP corresponde a cada error.

Arranque: `litmar servir` (ver `cli.py`); documentación interactiva en `/docs` y
una página web que usa la API en `/` (`web/index.html`).
"""

from __future__ import annotations

import logging
from importlib.metadata import version
from importlib.resources import files
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from litmar import agente, flujo, llm
from litmar.articulo import Articulo
from litmar.busqueda import buscar_en_fuentes
from litmar.configuracion import fuentes_disponibles, id_fuente, nombre_fuente
from litmar.idiomas import Idioma

MAX_RESULTADOS = 50  # artículos por fuente en /buscar

# Uvicorn ya configura este logger: lo que se escriba en él sale en su terminal.
_registro = logging.getLogger("uvicorn.error")


def _fuente_disponible(identificador: str) -> str:
    """«europepmc» o «Europe PMC» → «Europe PMC»; ValueError (→ 422) si no se puede usar."""
    nombre = nombre_fuente(identificador)
    if nombre not in fuentes_disponibles():
        raise ValueError(f"{nombre} no está configurada en el servidor (ver .env.example)")
    return nombre


# Una fuente válida: FastAPI aplica la comprobación a cada elemento de la lista,
# tanto en la URL (/buscar) como en el cuerpo (/revisiones).
Fuente = Annotated[str, AfterValidator(_fuente_disponible)]


# --- Modelos de salida ---------------------------------------------------------


class Salud(BaseModel):
    status: Literal["ok"] = "ok"
    version: str


class FuenteSalida(BaseModel):
    id: str = Field(description="Identificador para las peticiones, p. ej. «europepmc».")
    name: str = Field(description="Nombre para mostrar, p. ej. «Europe PMC».")


class ArticuloSalida(BaseModel):
    """Los mismos campos que `Articulo` y que el JSON de `Biblioteca`."""

    title: str
    authors: list[str]
    year: int
    doi: str
    journal: str
    abstract: str
    citations: int | None = Field(description="null: la fuente no da el recuento de citas.")

    @classmethod
    def desde(cls, articulo: Articulo) -> ArticuloSalida:
        return cls(
            title=articulo.title,
            authors=list(articulo.authors),
            year=articulo.year,
            doi=articulo.doi,
            journal=articulo.journal,
            abstract=articulo.abstract,
            citations=articulo.citations,
        )


class BusquedaSalida(BaseModel):
    query: str
    articles: list[ArticuloSalida] = Field(description="Sin DOI repetidos entre fuentes.")
    errors: list[str] = Field(description="Por qué falló cada fuente que no respondió.")
    failed: list[str] = Field(description="Nombres de las fuentes que fallaron.")


class RevisionEntrada(BaseModel):
    # Quita espacios al principio y al final: «   » cuenta como pregunta vacía.
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, description="La pregunta de investigación.")
    mode: Literal["flujo", "agente"] = Field(
        "flujo", description="flujo: pasos fijos (LangGraph); agente: decide el modelo."
    )
    # validate_default: el valor por defecto también pasa por _fuente_disponible.
    sources: list[Fuente] = Field(["openalex", "europepmc"], min_length=1, validate_default=True)
    n: int = Field(
        6,
        ge=1,
        le=flujo.MAX_SELECCIONADOS,
        description="Artículos que se resumen (flujo) o que elige el agente.",
    )
    since: int | None = Field(None, description="Solo artículos de ese año o posteriores.")
    language: Idioma = Field(
        "es",
        description="Idioma de la interfaz y del informe: es, pt-BR, en o ja.",
    )


class RevisionSalida(BaseModel):
    question: str
    mode: Literal["flujo", "agente"]
    language: Idioma
    report: str = Field(description="El informe en Markdown, con referencias y avisos.")
    bibtex: str = Field(description="BibTeX de los artículos citados (solo de esos).")
    cited: list[ArticuloSalida]
    queries: list[str] = Field(description="Las búsquedas que se hicieron.")
    warnings: list[str]


# --- Rutas ---------------------------------------------------------------------

app = FastAPI(
    title="litmar",
    version=version("litmar"),
    description="Busca literatura científica en varias fuentes y escribe revisiones que "
    "solo citan artículos reales.",
)


# Fuera del esquema: es la página para personas, no parte del contrato de la API.
@app.get("/", include_in_schema=False)
def pagina() -> HTMLResponse:
    """La web de litmar (HTML, CSS y JavaScript en un fichero) que usa esta API."""
    # Se lee del paquete instalado, no de la carpeta del repositorio: así funciona
    # igual con `uv run`, con `pip install` y dentro de Docker.
    return HTMLResponse(files("litmar").joinpath("web/index.html").read_text(encoding="utf-8"))


@app.get("/salud")
def salud() -> Salud:
    """Comprueba que el servidor responde."""
    return Salud(version=version("litmar"))


@app.get("/fuentes")
def fuentes() -> list[FuenteSalida]:
    """Fuentes que se pueden usar con la configuración del servidor."""
    return [FuenteSalida(id=id_fuente(nombre), name=nombre) for nombre in fuentes_disponibles()]


@app.get(
    "/buscar",
    responses={502: {"description": "Ninguna de las fuentes pedidas respondió."}},
)
def buscar(
    consulta: Annotated[str, Query(pattern=r"\S", description="Qué buscar.")],
    fuente: Annotated[
        list[Fuente],
        Query(
            description="Repítelo para buscar en varias: ?fuente=a&fuente=b",
            validate_default=True,  # también el valor por defecto pasa a «OpenAlex»
        ),
    ] = ["openalex"],  # noqa: B006 (FastAPI no modifica el valor por defecto)
    n: Annotated[int, Query(ge=1, le=MAX_RESULTADOS, description="Artículos por fuente.")] = 10,
    desde: Annotated[int | None, Query(description="Año mínimo de publicación.")] = None,
) -> BusquedaSalida:
    """Busca en varias fuentes y junta los resultados sin duplicar DOI.

    Si alguna fuente falla, se devuelve lo de las demás y el error en `errors`.
    """
    nombres = list(dict.fromkeys(fuente))  # sin repetir, en el orden pedido
    resultado = buscar_en_fuentes(consulta, nombres, n, desde=desde)
    if len(resultado.failed) == len(nombres):
        raise HTTPException(502, "Ninguna fuente respondió. " + " ".join(resultado.errors))
    return BusquedaSalida(
        query=consulta,
        articles=[ArticuloSalida.desde(a) for a in resultado.library],
        errors=resultado.errors,
        failed=resultado.failed,
    )


# `def` y no `async def`: la revisión tarda minutos y FastAPI la ejecuta en otro
# hilo, así que el servidor sigue atendiendo otras peticiones mientras tanto.
@app.post(
    "/revisiones",
    responses={
        502: {"description": "El modelo de lenguaje falló durante la revisión."},
        503: {"description": "Falta configurar el modelo en el .env del servidor."},
    },
)
def revisiones(entrada: RevisionEntrada) -> RevisionSalida:
    """Revisión de literatura con un modelo de lenguaje. Tarda varios minutos.

    Devuelve el informe y el BibTeX de lo citado; no guarda nada en disco. En
    modo agente no se piden aprobaciones (por HTTP no hay a quién preguntar).
    """
    try:
        modelo = llm.crear_modelo()
    except llm.ErrorDeConfiguracion as exc:  # su mensaje dice qué poner en el .env
        raise HTTPException(503, str(exc)) from exc

    revisar = flujo.revisar if entrada.mode == "flujo" else agente.revisar
    try:
        estado = revisar(
            modelo,
            entrada.question,
            fuentes=list(dict.fromkeys(entrada.sources)),
            n=entrada.n,
            desde=entrada.since,
            idioma=entrada.language,
            mostrar=_registro.info,
        )
    except Exception as exc:  # p. ej. un 429 del proveedor
        # Solo el tipo de error: el mensaje del proveedor podría incluir la petición.
        _registro.exception("La revisión falló")
        raise HTTPException(
            502, f"El modelo falló durante la revisión ({type(exc).__name__})."
        ) from exc

    citados = flujo.citados(estado)
    return RevisionSalida(
        question=entrada.question,
        mode=entrada.mode,
        language=entrada.language,
        report=flujo.informe_markdown(estado, entrada.language),
        bibtex=citados.a_bibtex(),
        cited=[ArticuloSalida.desde(a) for a in citados],
        queries=estado.get("queries", []),
        warnings=estado.get("warnings", []),
    )
