"""Flujo de revisión de literatura con LangGraph (Clase 2).

Seis pasos fijos que comparten un estado. Tres llaman al modelo y tres son
código normal, porque lo que se puede hacer con código es más barato y más
fiable:

    planificar (LLM) → buscar (código) → filtrar (código)
      → resumir_articulos (LLM) → sintetizar (LLM) → verificar_citas (código)
                                       ↑                    │
                                       └── citas inventadas: reescribir (máx. 2)

`verificar_citas` es el guardarraíl: el modelo puede inventar un DOI que suena
perfecto, y el código comprueba que cada DOI citado está entre los artículos
seleccionados. Si no, vuelve a `sintetizar`; tras `MAX_REESCRITURAS`, las citas
que sigan sin estar se sustituyen por «[cita no verificada]».

Diagrama (Mermaid):

    flowchart LR
        START --> planificar --> buscar --> resumir_articulos --> filtrar
        filtrar --> sintetizar --> verificar_citas
        verificar_citas -- "citas inventadas: reescribir (máx. 2)" --> sintetizar
        verificar_citas -- ok --> END

Este módulo no imprime nada: `describir_paso` da el texto de cada paso y la CLI
(o la interfaz web) decide cómo mostrarlo.
"""

from __future__ import annotations

import operator
import re
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from litmar.articulo import Articulo, normalizar_doi
from litmar.biblioteca import Biblioteca
from litmar.busqueda import buscar_en_fuentes
from litmar.fuentes import Fuente
from litmar.idiomas import INSTRUCCIONES, Idioma
from litmar.idiomas import texto as texto_de_idioma
from litmar.resumen import ResumenArticulo, resumir
from litmar.seleccion import aviso_citas_no_disponibles, ordenar_articulos

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

# Límites en el código, no en el prompt: el modelo no puede saltárselos.
MAX_CONSULTAS = 3
MAX_SELECCIONADOS = 10
MAX_REESCRITURAS = 2
RESULTADOS_POR_CONSULTA = 10  # por consulta y por fuente

NO_VERIFICADA = "cita no verificada"

# «[doi:10.1234/abc]» (el formato que pedimos) o «doi.org/10.1234/abc» (por si acaso).
_CITA = re.compile(r"(doi:\s*|doi\.org/)(10\.[\d.]+/[^\s;,\]\)]+)", re.IGNORECASE)


class EstadoRevision(TypedDict, total=False):
    """El diccionario que viaja por el grafo. Cada nodo devuelve solo lo que cambia."""

    question: str  # la pregunta de investigación
    queries: list[str]  # las búsquedas que propone planificar
    articles: list[Articulo]  # todo lo encontrado, sin duplicados
    selected: list[Articulo]  # los N que pasan el filtro
    summaries: dict[str, ResumenArticulo]  # DOI → resumen estructurado
    report: str  # la síntesis en Markdown, citando por DOI
    cited: list[str]  # DOI citados que sí están entre los seleccionados
    invalid: list[str]  # DOI citados que no están: inventados
    unverified: list[str]  # inválidos que quedaron marcados tras agotar las reescrituras
    rewrites: int  # cuántas veces se ha reescrito la síntesis
    # Con `operator.add`, LangGraph suma las listas en lugar de sustituirlas: cada
    # nodo devuelve solo sus avisos nuevos.
    warnings: Annotated[list[str], operator.add]


class Plan(BaseModel):
    """Búsquedas para encontrar artículos que respondan a la pregunta."""

    queries: list[str] = Field(
        description=(
            "Entre 2 y 3 búsquedas para bases de datos académicas (OpenAlex, Europe PMC…), "
            "en inglés, de 2 a 6 palabras clave cada una, sin operadores booleanos. "
            "Cada una debe cubrir un aspecto distinto de la pregunta."
        )
    )


_INSTRUCCIONES_PLAN = """\
Eres un documentalista científico. Convierte la pregunta de investigación en 2 o 3
búsquedas distintas para bases de datos académicas."""

_INSTRUCCIONES_SINTESIS = """\
Eres un investigador que escribe una síntesis breve de literatura científica.
Responde a la pregunta usando SOLO los artículos que se te dan.
- Cita cada afirmación con el DOI del artículo entre corchetes, exactamente así:
  [doi:10.1234/abcd]. Para dos artículos: [doi:10.1234/abcd] [doi:10.5678/efgh].
- Usa solo DOI de la lista. No cites ningún otro trabajo, aunque lo conozcas.
- Da más peso a los artículos más relevantes y no uses los de relevancia 1.
- Señala dónde coinciden y dónde discrepan los estudios, y qué no responde la evidencia.
- Escribe en Markdown, de 3 a 5 párrafos, sin título y sin lista de referencias
  (la añade el programa)."""


def extraer_dois(texto: str) -> list[str]:
    """DOI citados en `texto`, normalizados y sin repetir, en orden de aparición."""
    dois = []
    for coincidencia in _CITA.finditer(texto):
        try:
            doi = normalizar_doi(coincidencia.group(2).rstrip("."))
        except ValueError:
            continue
        if doi not in dois:
            dois.append(doi)
    return dois


def marcar_no_verificadas(texto: str, invalidos: Iterable[str], idioma: Idioma = "es") -> str:
    """Sustituye cada cita a un DOI de `invalidos` por «cita no verificada»."""
    invalidos = set(invalidos)
    marca = texto_de_idioma(idioma, "no_verificada")

    def sustituir(coincidencia: re.Match[str]) -> str:
        try:
            doi = normalizar_doi(coincidencia.group(2).rstrip("."))
        except ValueError:
            return coincidencia.group(0)
        return marca if doi in invalidos else coincidencia.group(0)

    return _CITA.sub(sustituir, texto)


def _ficha(articulo: Articulo, resumen: ResumenArticulo) -> str:
    """Lo que ve el modelo de cada artículo al sintetizar: el resumen estructurado."""
    hallazgos = "\n".join(f"  - {h}" for h in resumen.findings)
    return (
        f"DOI: {articulo.doi}\n"
        f"Referencia: {articulo.short_citation}. {articulo.title}\n"
        f"Relevancia para la pregunta: {resumen.relevance}/5\n"
        f"Objetivo: {resumen.objective}\n"
        f"Método: {resumen.method}\n"
        f"Hallazgos:\n{hallazgos}\n"
        f"Limitaciones: {resumen.limitations}"
    )


def _quedan_reescrituras(estado: EstadoRevision) -> bool:
    return estado.get("rewrites", 0) < MAX_REESCRITURAS


def crear_flujo(
    modelo: BaseChatModel,
    *,
    fuentes: Iterable[str] = ("OpenAlex",),
    n: int = 6,
    desde: int | None = None,
    idioma: Idioma = "es",
    crear_fuente: Callable[[str], Fuente] | None = None,
):
    """Construye y compila el grafo de revisión.

    `n` es cuántos artículos se resumen (como mucho `MAX_SELECCIONADOS`).
    `crear_fuente` permite pasar fuentes falsas en los tests.
    """
    fuentes = list(fuentes)
    n = max(1, min(n, MAX_SELECCIONADOS))

    # --- Nodos: funciones normales que reciben el estado y devuelven lo que cambian.

    def planificar(estado: EstadoRevision) -> EstadoRevision:  # LLM
        pregunta = estado["question"]
        plan = modelo.with_structured_output(Plan, method="json_schema").invoke(
            [("system", _INSTRUCCIONES_PLAN), ("human", pregunta)]
        )
        consultas = list(dict.fromkeys(q.strip() for q in plan.queries if q.strip()))
        return {"queries": consultas[:MAX_CONSULTAS] or [pregunta]}

    def buscar(estado: EstadoRevision) -> EstadoRevision:  # código
        encontrados = Biblioteca()
        avisos: list[str] = []
        for consulta in estado["queries"]:
            resultado = buscar_en_fuentes(
                consulta, fuentes, RESULTADOS_POR_CONSULTA, desde=desde, crear=crear_fuente
            )
            for articulo in resultado.library:
                encontrados.agregar(articulo)
            avisos += [f"«{consulta}»: {error}" for error in resultado.errors]
        return {"articles": list(encontrados), "warnings": avisos}

    def resumir_articulos(estado: EstadoRevision) -> EstadoRevision:  # LLM
        resumenes: dict[str, ResumenArticulo] = {}
        avisos: list[str] = []
        for articulo in estado["articles"]:
            if not articulo.abstract.strip():
                continue
            try:
                resumen = resumir(articulo, estado["question"], modelo, idioma=idioma)
            except Exception as error:  # un artículo que falla no para la revisión
                avisos.append(f"No se pudo resumir {articulo.doi}: {type(error).__name__}")
                continue
            if resumen is not None:
                resumenes[articulo.doi] = resumen
        return {"summaries": resumenes, "warnings": avisos}

    def filtrar(estado: EstadoRevision) -> EstadoRevision:  # código
        resumenes = estado.get("summaries", {})
        relevancias = {doi: resumen.relevance for doi, resumen in resumenes.items()}
        seleccionados = ordenar_articulos(estado["articles"], relevancias)[:n]
        cambios: EstadoRevision = {"selected": seleccionados}
        aviso = aviso_citas_no_disponibles(seleccionados)
        if aviso:
            cambios["warnings"] = [aviso]
        return cambios

    def sintetizar(estado: EstadoRevision) -> EstadoRevision:  # LLM
        resumenes = estado.get("summaries", {})
        if not resumenes:  # sin artículos no hay nada que sintetizar: no se llama al modelo
            return {"report": texto_de_idioma(idioma, "no_articulos")}

        fichas = "\n\n".join(
            _ficha(articulo, resumenes[articulo.doi])
            for articulo in estado["selected"]
            if articulo.doi in resumenes
        )
        mensajes = [
            ("system", f"{_INSTRUCCIONES_SINTESIS}\n{INSTRUCCIONES[idioma]}"),
            ("human", f"Pregunta: {estado['question']}\n\nArtículos:\n\n{fichas}"),
        ]
        cambios: EstadoRevision = {}
        if estado.get("invalid"):  # venimos de verificar_citas: reescribir
            mensajes += [
                ("ai", estado["report"]),
                (
                    "human",
                    "Estos DOI no están en la lista de artículos: "
                    f"{', '.join(estado['invalid'])}. Reescribe la síntesis citando solo "
                    "DOI de la lista.",
                ),
            ]
            cambios["rewrites"] = estado.get("rewrites", 0) + 1
        cambios["report"] = modelo.invoke(mensajes).text
        return cambios

    def verificar_citas(estado: EstadoRevision) -> EstadoRevision:  # código
        seleccionados = {articulo.doi for articulo in estado.get("selected", [])}
        citados = extraer_dois(estado["report"])
        validos = [doi for doi in citados if doi in seleccionados]
        invalidos = [doi for doi in citados if doi not in seleccionados]
        cambios: EstadoRevision = {"cited": validos, "invalid": invalidos}
        if invalidos and not _quedan_reescrituras(estado):
            cambios["report"] = marcar_no_verificadas(estado["report"], invalidos, idioma)
            cambios["unverified"] = invalidos
            cambios["warnings"] = [
                f"Tras {MAX_REESCRITURAS} reescrituras seguían citados DOI que no estaban "
                f"entre los seleccionados ({', '.join(invalidos)}): marcados como "
                f"«{texto_de_idioma(idioma, 'no_verificada')}»."
            ]
        return cambios

    # --- Arista condicional: mira el estado y elige el camino.

    def decidir(estado: EstadoRevision) -> str:
        if estado.get("invalid") and _quedan_reescrituras(estado):
            return "reescribir"
        return "fin"

    grafo = StateGraph(EstadoRevision)
    grafo.add_node("planificar", planificar)
    grafo.add_node("buscar", buscar)
    grafo.add_node("resumir_articulos", resumir_articulos)
    grafo.add_node("filtrar", filtrar)
    grafo.add_node("sintetizar", sintetizar)
    grafo.add_node("verificar_citas", verificar_citas)

    grafo.add_edge(START, "planificar")
    grafo.add_edge("planificar", "buscar")
    grafo.add_edge("buscar", "resumir_articulos")
    grafo.add_edge("resumir_articulos", "filtrar")
    grafo.add_edge("filtrar", "sintetizar")
    grafo.add_edge("sintetizar", "verificar_citas")
    grafo.add_conditional_edges(
        "verificar_citas", decidir, {"reescribir": "sintetizar", "fin": END}
    )
    return grafo.compile()


def estado_inicial(pregunta: str) -> EstadoRevision:
    return {"question": pregunta, "rewrites": 0, "warnings": []}


def revisar(
    modelo: BaseChatModel,
    pregunta: str,
    *,
    fuentes: Iterable[str] = ("OpenAlex",),
    n: int = 6,
    desde: int | None = None,
    idioma: Idioma = "es",
    mostrar: Callable[[str], None] = lambda linea: None,
    avisar: Callable[[str], None] | None = None,
) -> EstadoRevision:
    """Ejecuta el flujo completo y devuelve el estado final.

    Cada paso se pasa a `mostrar` en cuanto termina (la CLI lo imprime, la UI lo
    escribe en pantalla); los avisos, a `avisar` (por defecto, también a `mostrar`).
    """
    avisar = avisar or mostrar
    flujo = crear_flujo(modelo, fuentes=fuentes, n=n, desde=desde, idioma=idioma)
    estado = estado_inicial(pregunta)
    # "updates": lo que cambia cada nodo, para mostrarlo; "values": el estado completo.
    for modo, datos in flujo.stream(estado, stream_mode=["updates", "values"]):
        if modo == "values":
            estado = datos
            continue
        for nodo, cambios in datos.items():
            mostrar(f"> {nodo:<18} {describir_paso(nodo, cambios)}")
            for aviso in cambios.get("warnings", []):
                avisar(f"  Aviso: {aviso}")
    return estado


def _plural(numero: int, singular: str, plural: str) -> str:
    return f"{numero} {singular if numero == 1 else plural}"


def describir_paso(nodo: str, cambios: EstadoRevision) -> str:
    """Una línea que resume lo que acaba de hacer `nodo`, como en la demo de clase."""
    if nodo == "planificar":
        return _plural(len(cambios["queries"]), "consulta", "consultas")
    if nodo == "buscar":
        return _plural(len(cambios["articles"]), "artículo", "artículos")
    if nodo == "filtrar":
        return _plural(len(cambios["selected"]), "seleccionado", "seleccionados")
    if nodo == "resumir_articulos":
        return _plural(len(cambios["summaries"]), "resumen", "resúmenes")
    if nodo == "sintetizar":
        return f"informe ({_plural(len(extraer_dois(cambios['report'])), 'cita', 'citas')})"
    if nodo == "verificar_citas":
        invalidos = cambios["invalid"]
        if not invalidos:
            return "ok"
        texto = _plural(len(invalidos), "cita inválida", "citas inválidas")
        if cambios.get("unverified"):
            return f"{texto} → marcadas como «{NO_VERIFICADA}»"
        return f"{texto} → reescribir"
    return ""


def citados(estado: EstadoRevision) -> Biblioteca:
    """Los artículos citados (y verificados) en el informe, en orden de aparición."""
    por_doi = {articulo.doi: articulo for articulo in estado.get("selected", [])}
    return Biblioteca(por_doi[doi] for doi in estado.get("cited", []) if doi in por_doi)


_CITA_ENTRE_CORCHETES = re.compile(r"\[doi:\s*(10\.[\d.]+/[^\s;,\]\)]+)\]", re.IGNORECASE)


def enlazar_dois(texto: str) -> str:
    """Convierte cada «[doi:10.1234/abc]» en un enlace Markdown a doi.org."""
    return _CITA_ENTRE_CORCHETES.sub(
        lambda c: f"[doi:{c.group(1)}](https://doi.org/{c.group(1)})", texto
    )


def informe_markdown(estado: EstadoRevision, idioma: Idioma = "es") -> str:
    """El informe completo: pregunta, búsquedas, síntesis y referencias.

    Las referencias las escribe el código a partir de los artículos citados, no
    el modelo: así solo aparecen artículos reales.
    """
    partes = [f"# {estado['question']}", ""]
    if estado.get("queries"):
        busquedas = ", ".join(f"«{q}»" for q in estado["queries"])
        partes += [f"_{texto_de_idioma(idioma, 'busquedas')}: {busquedas}._", ""]
    partes += [estado.get("report", "").strip(), ""]
    referencias = citados(estado)
    if len(referencias):
        partes += [f"## {texto_de_idioma(idioma, 'referencias')}", ""]
        partes += [
            f"- {a.short_citation}. {a.title}. *{a.journal}*. https://doi.org/{a.doi}"
            for a in referencias
        ]
        partes.append("")
    if estado.get("warnings"):
        partes += (
            [f"## {texto_de_idioma(idioma, 'avisos')}", ""]
            + [f"- {aviso}" for aviso in estado["warnings"]]
            + [""]
        )
    return "\n".join(partes)
