"""Agente revisor con Deep Agents: el segundo modo de `litmar revisar` (Clase 2).

En el flujo (`flujo.py`) decidimos nosotros los pasos; aquí los decide el
modelo. Para que no se desmadre, todo lo que puede hacer está acotado en el
código:

- **Agente principal**: planifica con una lista de tareas (`write_todos`),
  encarga las búsquedas al subagente `buscador` (`task`), consulta las fuentes
  (`listar_fuentes`) y escribe el informe en `/informe.md` (`write_file`). Los
  ficheros son virtuales: viven en el estado del grafo (`StateBackend`), no en
  el disco. No tiene `edit_file`, `delete`, `glob`, `grep` ni `execute`.
- **Subagente `buscador`**: solo `buscar_articulos`, `listar_fuentes` y
  `read_file`. Trabaja en su propio contexto y devuelve al principal un resumen
  de lo encontrado, no decenas de artículos. Deep Agents añade además un
  subagente `general-purpose` con las herramientas del principal: no puede
  buscar (quitarlo exige registrar un perfil global por modelo).
- **Límites**: `MAX_PASOS` llamadas al modelo para el principal,
  `MAX_PASOS_BUSCADOR` por encargo al buscador y `MAX_BUSQUEDAS` búsquedas en
  total. Si el principal llega a su límite, el informe dice hasta dónde llegó.
- **Aprobación humana** (`aprobar=True`): el grafo se detiene antes de cada
  `buscar_articulos` para que una persona la apruebe, la edite o la rechace.
- **Citas comprobadas con código**: cada búsqueda guarda en un `Registro` los
  artículos devueltos. Al final, cada DOI citado se busca en ese registro; los
  que no estén se marcan como «[cita no verificada]», igual que en el flujo.

El informe y el BibTeX salen de `flujo.informe_markdown` y `flujo.citados`:
mismo formato que el flujo, para poder compararlos.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware import FilesystemMiddleware
from langchain.agents.middleware import ModelCallLimitMiddleware, TodoListMiddleware
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from litmar import herramientas
from litmar.articulo import Articulo
from litmar.flujo import EstadoRevision, extraer_dois, marcar_no_verificadas
from litmar.idiomas import INSTRUCCIONES as INSTRUCCIONES_IDIOMA
from litmar.idiomas import Idioma
from litmar.idiomas import texto as texto_de_idioma
from litmar.seleccion import PESO_CITAS, PESO_RELEVANCIA, aviso_citas_no_disponibles

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

MAX_PASOS = 25  # llamadas al modelo del agente principal
MAX_PASOS_BUSCADOR = 8  # llamadas al modelo por cada encargo al buscador
MAX_BUSQUEDAS = 12  # llamadas a buscar_articulos en toda la revisión
RUTA_INFORME = "/informe.md"

# Lo que escribe ModelCallLimitMiddleware cuando corta al agente.
_LIMITE_ALCANZADO = "Model call limits exceeded"

INSTRUCCIONES = """\
Eres un revisor de literatura científica. Respondes a una pregunta de investigación
con un informe breve que solo cita artículos reales.

Cómo trabajar:
1. Antes de buscar, planifica con write_todos: de 3 a 5 tareas (una por cada aspecto
   de la pregunta que haya que buscar, y la última, escribir el informe). Márcalas
   como hechas a medida que avances.
2. No buscas tú: encarga cada búsqueda al subagente «buscador» con la herramienta
   task. Cada encargo, concreto: qué aspecto, qué palabras clave en inglés y en qué
   fuente. Busca en varias fuentes de estas: {fuentes}. Puedes usar listar_fuentes
   para ver qué contiene cada una.
3. Con lo que te devuelva el buscador, elige como mucho {n} artículos y escribe el
   informe en {ruta} con write_file. Después, termina con una frase breve.
   Considera primero la relevancia para la pregunta (1–5). Si hay citas, combina
   {peso_relevancia:.0%} de relevancia con {peso_citas:.0%} del «Ajuste por citas»
   que da la herramienta. Ese ajuste usa tasa = citas / max(1, año actual - año
   de publicación + 1), transformada a 1–5 con 1 + 4 × tasa / (1 + tasa). Si
   pone «Citas: no disponible», usa solo la relevancia; no lo trates como cero.

Reglas del informe:
- En el idioma seleccionado y en Markdown, de 3 a 5 párrafos, sin título y sin lista de referencias
  (la añade el programa).
- Cita cada afirmación con el DOI entre corchetes, exactamente así: [doi:10.1234/abcd].
- Cita solo DOI que te haya devuelto el buscador. Nunca cites de memoria: el programa
  comprueba cada DOI y marca los que no salieron de las búsquedas.
- Termina con una sección cuyo título traduzca «Lo que no se encontró» al idioma
  seleccionado: qué aspectos de la pregunta no cubren los artículos encontrados
  y qué búsquedas no dieron resultado.
- PANGAEA devuelve conjuntos de datos, no artículos: úsalos solo como apoyo.
- Si no encuentras nada útil, dilo en el informe en lugar de rellenarlo."""

INSTRUCCIONES_BUSCADOR = """\
Eres un buscador bibliográfico. Recibes un encargo (qué buscar y dónde) y lo resuelves
con buscar_articulos. Haz como mucho 3 búsquedas por encargo; si no hay resultados o
la fuente falla, prueba otras palabras clave en inglés u otra fuente de la lista.

Devuelve solo lo relevante para el encargo. Para cada artículo útil: el DOI copiado
tal cual, el título, el año, su relevancia para el encargo (1–5), el ajuste por
citas que muestra la herramienta y una o dos frases de lo que aporta según su
resumen. Si el recuento no está disponible, indícalo literalmente y evalúa el
artículo solo por su relevancia. No descartes un artículo solo porque no tenga
recuento. Descarta los que no tengan resumen o no traten el tema. Di también qué
no encontraste. No inventes DOI ni datos."""

DESCRIPCION_BUSCADOR = (
    "Busca artículos científicos sobre un aspecto concreto en las fuentes de litmar y "
    "devuelve solo los relevantes, con su DOI exacto. Encárgale una cosa cada vez: qué "
    "buscar, con qué palabras clave y en qué fuente."
)


@dataclass
class Registro:
    """Lo que han devuelto las búsquedas: la base para comprobar las citas en código."""

    articles: dict[str, Articulo] = field(default_factory=dict)  # DOI → artículo
    searches: list[str] = field(default_factory=list)  # «consulta» (fuente), en orden
    _cerrojo: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def anotar(self, consulta: str, fuente: str, articulos: Iterable[Articulo]) -> None:
        with self._cerrojo:  # el agente puede lanzar varios buscadores a la vez
            self.searches.append(f"{consulta} ({fuente})")
            for articulo in articulos:
                self.articles.setdefault(articulo.doi, articulo)


def _herramientas(
    registro: Registro, fuentes: list[str], desde: int | None = None
) -> list[StructuredTool]:
    """`buscar_articulos` y `listar_fuentes` limitadas a `fuentes` y que anotan en `registro`.

    Mismo nombre, descripción y argumentos que las de `herramientas.py` (el modelo
    ve lo mismo); lo que cambia es que guardan lo que devuelven.
    """

    def buscar_articulos(consulta: str, fuente: str = "OpenAlex", n: int = 5) -> str:
        if len(registro.searches) >= MAX_BUSQUEDAS:
            return (
                f"Error: ya se han hecho {MAX_BUSQUEDAS} búsquedas, el máximo de esta "
                "revisión. Trabaja con lo que ya tienes."
            )
        texto, articulos = herramientas.buscar(consulta, fuente, n, permitidas=fuentes, desde=desde)
        registro.anotar(consulta.strip(), fuente, articulos)
        return texto

    def listar_fuentes() -> str:
        return herramientas.describir_fuentes(fuentes)

    original_buscar = herramientas.buscar_articulos
    original_listar = herramientas.listar_fuentes
    return [
        StructuredTool.from_function(
            buscar_articulos,
            name=original_buscar.name,
            description=original_buscar.description,
            args_schema=original_buscar.args_schema,
        ),
        StructuredTool.from_function(
            listar_fuentes,
            name=original_listar.name,
            description=original_listar.description,
            args_schema=original_listar.args_schema,
        ),
    ]


def crear_agente(
    modelo: BaseChatModel,
    registro: Registro,
    *,
    fuentes: Iterable[str] = ("OpenAlex", "Europe PMC"),
    n: int = 6,
    desde: int | None = None,
    idioma: Idioma = "es",
    aprobar: bool = False,
):
    """Construye el agente revisor. Devuelve un grafo de LangGraph, como el flujo."""
    fuentes = list(fuentes)
    buscar, listar = _herramientas(registro, fuentes, desde)
    backend = StateBackend()  # ficheros virtuales en el estado, nada en el disco
    buscador = {
        "name": "buscador",
        "description": DESCRIPCION_BUSCADOR,
        "system_prompt": INSTRUCCIONES_BUSCADOR,
        "tools": [buscar, listar],
        "middleware": [
            FilesystemMiddleware(backend=backend, tools=["read_file"]),
            ModelCallLimitMiddleware(run_limit=MAX_PASOS_BUSCADOR, exit_behavior="end"),
        ],
    }
    return create_deep_agent(
        model=modelo,
        tools=[listar],
        system_prompt=INSTRUCCIONES.format(
            fuentes=", ".join(fuentes),
            n=n,
            ruta=RUTA_INFORME,
            peso_relevancia=PESO_RELEVANCIA,
            peso_citas=PESO_CITAS,
        )
        + "\n\n"
        + INSTRUCCIONES_IDIOMA[idioma],
        middleware=[
            TodoListMiddleware(),  # write_todos: la lista de tareas
            FilesystemMiddleware(backend=backend, tools=["ls", "read_file", "write_file"]),
            ModelCallLimitMiddleware(thread_limit=MAX_PASOS, exit_behavior="end"),
        ],
        subagents=[buscador],
        backend=backend,
        # El subagente hereda interrupt_on: se pide permiso antes de cada búsqueda.
        interrupt_on=(
            {"buscar_articulos": {"allowed_decisions": ["approve", "edit", "reject"]}}
            if aprobar
            else None
        ),
        checkpointer=MemorySaver(),  # necesario para pausar y reanudar
    )


def configuracion() -> dict[str, Any]:
    """Configuración de una ejecución: un hilo nuevo (la conversación del checkpointer)."""
    return {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 1000}


def entrada(pregunta: str) -> dict[str, Any]:
    return {"messages": [{"role": "user", "content": pregunta}]}


class Narrador:
    """Convierte el stream del agente en líneas legibles, como en la demo de clase.

    Se usa con `stream(..., stream_mode="updates", subgraphs=True)`: cada elemento
    es `(espacio, actualizacion)`; `espacio` vacío es el agente principal y
    `("tools:…",)`, un subagente.
    """

    def __init__(self) -> None:
        self._tareas_mostradas = False

    def lineas(self, espacio: tuple[str, ...], actualizacion: dict[str, Any]) -> list[str]:
        lineas: list[str] = []
        for nodo, cambios in actualizacion.items():
            if not isinstance(cambios, dict):
                continue
            for mensaje in cambios.get("messages", []):
                if not isinstance(mensaje, AIMessage):
                    continue
                # El aviso de límite lo añade el middleware, no el nodo del modelo.
                if str(mensaje.content).startswith(_LIMITE_ALCANZADO):
                    quien = "el buscador" if espacio else "el agente"
                    lineas.append(f"! Límite de pasos alcanzado: {quien} se detiene.")
                if nodo == "model":
                    for llamada in mensaje.tool_calls:
                        lineas += self._llamada(llamada["name"], llamada["args"], bool(espacio))
        return lineas

    def _llamada(self, nombre: str, argumentos: dict[str, Any], en_subagente: bool) -> list[str]:
        if nombre == "write_todos":
            return self._tareas(argumentos.get("todos", []))
        prefijo = "    · " if en_subagente else "→ "  # lo del buscador, sangrado
        if nombre == "task":
            tipo = argumentos.get("subagent_type", "?")
            return [f"{prefijo}task({tipo}): {_una_linea(argumentos.get('description', ''))}"]
        if nombre == "buscar_articulos":
            consulta = argumentos.get("consulta", "")
            fuente = argumentos.get("fuente", "OpenAlex")
            n = argumentos.get("n", 5)
            return [f"{prefijo}buscar_articulos(«{consulta}», {fuente}, n={n})"]
        if nombre in ("write_file", "read_file"):
            return [f"{prefijo}{nombre}({argumentos.get('file_path', '').lstrip('/')})"]
        return [f"{prefijo}{nombre}()"]

    def _tareas(self, tareas: list[dict[str, Any]]) -> list[str]:
        """La primera vez, la lista entera; después, cuántas van hechas."""
        hechas = sum(1 for t in tareas if t.get("status") == "completed")
        if not self._tareas_mostradas:
            self._tareas_mostradas = True
            return [f"{_casilla(t)} {t.get('content', '')}" for t in tareas]
        return [f"[x] {hechas}/{len(tareas)} tareas"]


def _casilla(tarea: dict[str, Any]) -> str:
    return {"completed": "[x]", "in_progress": "[~]"}.get(tarea.get("status"), "[ ]")


def _una_linea(texto: str, largo: int = 90) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"


def ejecutar(
    agente,
    config: dict[str, Any],
    pregunta: str,
    *,
    mostrar: Callable[[str], None],
    decidir: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    """Ejecuta el agente hasta el final, mostrando cada paso y pidiendo aprobaciones.

    `mostrar` recibe cada línea del `Narrador`; `decidir` recibe cada búsqueda que
    espera aprobación (`{"name", "args", …}`) y devuelve la decisión
    (`{"type": "approve"}`, `"reject"` o `"edit"`).

    Con `aprobar=True` el grafo se detiene antes de cada búsqueda. Si el agente
    lanzó varios buscadores a la vez, puede haber varias pausas pendientes: se
    contesta a todas y se reanuda indicando a qué interrupción va cada respuesta
    (por su `id`). Una interrupción de un subagente llega dos veces al stream (en
    su espacio y en el del principal); solo cuenta la del principal.
    """
    narrador = Narrador()
    entrada_: Any = entrada(pregunta)
    while True:  # una vuelta por cada pausa para pedir aprobación
        pendientes: dict[str, Any] = {}
        for espacio, actualizacion in agente.stream(
            entrada_, config, stream_mode="updates", subgraphs=True
        ):
            for linea in narrador.lineas(espacio, actualizacion):
                mostrar(linea)
            if not espacio:
                for interrupcion in actualizacion.get("__interrupt__", ()):
                    pendientes[interrupcion.id] = interrupcion
        if not pendientes:
            return
        respuestas = {
            id_: {"decisions": [decidir(accion) for accion in i.value["action_requests"]]}
            for id_, i in pendientes.items()
        }
        entrada_ = Command(resume=respuestas)


def revisar(
    modelo: BaseChatModel,
    pregunta: str,
    *,
    fuentes: Iterable[str] = ("OpenAlex", "Europe PMC"),
    n: int = 6,
    desde: int | None = None,
    idioma: Idioma = "es",
    aprobar: bool = False,
    mostrar: Callable[[str], None] = lambda linea: None,
    decidir: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> EstadoRevision:
    """Crea el agente, lo ejecuta y devuelve el estado final con las citas comprobadas.

    Sin `decidir`, se aprueba todo (solo se usa con `aprobar=True`).
    """
    registro = Registro()
    revisor = crear_agente(
        modelo, registro, fuentes=fuentes, n=n, desde=desde, idioma=idioma, aprobar=aprobar
    )
    config = configuracion()
    ejecutar(
        revisor,
        config,
        pregunta,
        mostrar=mostrar,
        decidir=decidir or (lambda accion: {"type": "approve"}),
    )
    return estado_final(revisor, config, pregunta, registro, idioma)


def estado_final(
    agente,
    config: dict[str, Any],
    pregunta: str,
    registro: Registro,
    idioma: Idioma = "es",
) -> EstadoRevision:
    """El resultado del agente con la forma del estado del flujo, citas ya comprobadas.

    Así `flujo.informe_markdown` y `flujo.citados` producen el mismo informe y el
    mismo BibTeX que en `--modo flujo`.
    """
    valores = agente.get_state(config).values
    mensajes = valores.get("messages", [])
    informe = _contenido(valores.get("files", {}).get(RUTA_INFORME))
    if not informe:  # si no escribió el fichero, su última respuesta
        finales = [
            m.text
            for m in mensajes
            if isinstance(m, AIMessage) and not str(m.content).startswith(_LIMITE_ALCANZADO)
        ]
        informe = finales[-1] if finales else ""

    avisos: list[str] = []
    if any(
        isinstance(m, AIMessage) and str(m.content).startswith(_LIMITE_ALCANZADO) for m in mensajes
    ):
        avisos.append(texto_de_idioma(idioma, "limite_agente").format(max_pasos=MAX_PASOS))
        informe = (
            (informe or f"_{texto_de_idioma(idioma, 'sin_informe_agente')}_")
            + f"\n\n## {texto_de_idioma(idioma, 'hasta_donde')}\n\n"
            + f"{texto_de_idioma(idioma, 'agente_detencion')}\n\n"
            + "\n".join(f"- {_casilla(t)} {t.get('content', '')}" for t in valores.get("todos", []))
        )

    citados = extraer_dois(informe)
    validos = [doi for doi in citados if doi in registro.articles]
    invalidos = [doi for doi in citados if doi not in registro.articles]
    if invalidos:
        informe = marcar_no_verificadas(informe, invalidos, idioma)
        marca = texto_de_idioma(idioma, "no_verificada")
        avisos.append(
            f"{texto_de_idioma(idioma, 'doi_no_busqueda')} ({', '.join(invalidos)}): "
            f"{texto_de_idioma(idioma, 'marca_no_verificada').format(marca=marca)}"
        )
    aviso = aviso_citas_no_disponibles(
        registro.articles[doi] for doi in validos if doi in registro.articles
    )
    if aviso:
        avisos.append(aviso)
    return {
        "question": pregunta,
        "queries": list(registro.searches),
        "selected": list(registro.articles.values()),
        "report": informe.strip() or "El agente no escribió ningún informe.",
        "cited": validos,
        "invalid": invalidos,
        "unverified": invalidos,
        "warnings": avisos,
    }


def _contenido(fichero: Any) -> str:
    """Texto de un fichero del `StateBackend` (str, o lista de líneas en versiones antiguas)."""
    if not fichero:
        return ""
    contenido = fichero.get("content", "") if isinstance(fichero, dict) else fichero
    return "\n".join(contenido) if isinstance(contenido, list) else str(contenido)
