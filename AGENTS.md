# AGENTS.md — guía para agentes que trabajan en litmar

Este fichero es el punto de entrada para cualquier agente (Claude Code, Codex,
Cursor…) y para cualquier persona que retome el proyecto. Explica qué es litmar,
cómo está hecho, qué reglas seguir y, sobre todo, **cómo se conserva la memoria
entre sesiones** para que cada sesión empiece donde terminó la anterior.

---

## 1. Memoria entre sesiones (léelo primero)

Un agente no recuerda nada de una sesión a otra. Todo lo que haga falta saber
tiene que estar escrito en el repositorio. Estos son los ficheros de memoria:

| Fichero | Qué guarda | Cómo se actualiza |
| --- | --- | --- |
| `AGENTS.md` (este) | Lo **estable**: qué es el proyecto, estructura, comandos, convenciones, reglas de seguridad, trampas conocidas, y este flujo. | Se edita cuando cambia algo estable (un módulo nuevo, una convención, una trampa descubierta). |
| `PROGRESS.md` | Lo **vivo**: estado actual, próximos pasos, cosas pendientes de terceros y el registro de cada sesión. | En **cada** sesión que haga trabajo (ver abajo). |
| `DECISIONS.md` | Las **decisiones** de diseño y de proceso, con su porqué, para no volver a discutirlas. | Cuando se toma o se cambia una decisión. Las antiguas no se borran: se marcan como sustituidas. |
| `CLAUDE.md` | Solo importa este fichero (`@AGENTS.md`), porque Claude Code lee `CLAUDE.md` y no `AGENTS.md`. | No hace falta tocarlo. |
| `.claude/hooks/` | Automatización para Claude Code (ver «Hooks»). | Solo si cambia el flujo. |

### Al empezar una sesión

1. **Lee `PROGRESS.md`** (en Claude Code, el hook de inicio ya inyecta su
   estado actual, los próximos pasos y la última entrada del registro).
2. **Sincroniza y mira qué ha cambiado fuera:**
   ```bash
   git fetch origin && git status -sb     # ¿hay commits nuevos en origin/main?
   gh pr list                              # ¿PRs nuevas de colaboradores?
   ```
   Si `main` va por detrás, avisa al usuario antes de hacer `git pull`.
3. Si la tarea toca una decisión ya tomada, **consulta `DECISIONS.md`** antes de
   proponer otra cosa.
4. Repasa **§10 (cómo trabaja el usuario)** y, si la tarea es revisar PRs,
   **§11**. Si el encargo parece sacado de una diapositiva, búscalo en `docs/`
   (ver §10).

### Durante la sesión

- Si descubres una trampa (algo que falla de forma no obvia), añádela a la
  sección 9 de este fichero en el momento, no al final.
- Si se toma una decisión con alternativas reales, anótala en `DECISIONS.md`.

### Al terminar una tarea (lo hace el agente, sin que se lo pidan)

Antes de dar una tarea por terminada, actualiza `PROGRESS.md`:

1. **«Estado actual»**: reescríbelo para que sea cierto *ahora* (commit de
   `main`, número de tests, funcionalidades, PRs abiertas).
2. **«Próximos pasos»**: tacha o quita lo hecho, añade lo que haya surgido.
3. **«Registro de sesiones»**: añade o amplía la entrada de **hoy** (las más
   nuevas arriba) con qué se hizo, qué se decidió, qué quedó a medias y por qué.
   Escribe para alguien que no estuvo: commits, números de PR, ficheros, y el
   motivo de las cosas.
4. Si hay commit, **`PROGRESS.md` va en el mismo commit** que el trabajo.

Lo que se ha preguntado y respondido sin cambiar nada (dudas, explicaciones) no
necesita entrada, salvo que el usuario haya expresado una preferencia o tomado
una decisión: eso sí se anota.

### Qué NO va en los ficheros de memoria

Estos ficheros son públicos (están en GitHub y los leen los colaboradores):

- Nada de claves, tokens, contenido de `.env` ni correos personales.
- Nada que ya cuente git o el código (diffs, listados de funciones): resume y
  enlaza al commit o al fichero.
- Nada de memoria privada del agente: la memoria del proyecto vive aquí, no en
  la memoria interna de cada herramienta.

### Hooks (Claude Code)

Configurados en `.claude/settings.json`:

- **`SessionStart` → `.claude/hooks/contexto-inicial.sh`**: al abrir, reanudar o
  compactar una sesión, inyecta el estado de `PROGRESS.md`, las dos últimas entradas del
  registro y el estado de git. Así la sesión arranca con contexto aunque nadie lo
  pida.
- **`Stop` → `.claude/hooks/recordar-progreso.sh`**: cuando el agente va a
  terminar su turno, comprueba si hay trabajo sin anotar (cambios sin commit o
  commits posteriores al último cambio de `PROGRESS.md`) y, si `PROGRESS.md` no
  se ha tocado, le pide una vez que lo actualice. No bloquea dos veces seguidas.

Otros agentes no tienen estos hooks: para ellos manda este fichero.

---

## 2. Qué es litmar

Herramienta de Python para reunir literatura científica de varias fuentes en una
sola biblioteca: busca en APIs públicas, convierte cada resultado a un modelo
común (`Articulo`), elimina duplicados por DOI y exporta a BibTeX, CSV o JSON.
Se usa como librería, desde la línea de comandos (`litmar buscar/exportar`) o
con una interfaz web (`litmar ui`, Streamlit).

- Repositorio: <https://github.com/Sapere-IA/litmar> (rama `main`, **público**).
- Mantenedor: Roberto Bada (Sapere IA).
- El usuario habla en **español**: responde en español.

### Contexto: es el proyecto de un curso

litmar es el proyecto que se construye en directo en el curso **«Python avanzado
para proyectos robustos, colaborativos y reproducibles»** (Institut de Ciències
del Mar, tres clases, imparte Roberto Bada). Las diapositivas están en `docs/`
(`docs/Clase1.pdf`, `docs/Clase2.pdf`). Consecuencias:

- **Los colaboradores son alumnos.** Hacen fork, trabajan en una rama y mandan
  PRs al repositorio del curso; el mantenedor integra algunas. Al revisarlas:
  tono didáctico, explicar el porqué, preguntas antes que órdenes.
- **Es material docente**: el código debe ser claro y fácil de explicar, con el
  patrón «concepto → para qué sirve → cómo se pide → cómo se comprueba».
- **Hoja de ruta del curso** (lo que viene; detalle en `PROGRESS.md`):
  - Clase 1 · *Busca* (17/11/2026, según la portada): fuentes, biblioteca, CLI,
    UI Streamlit, `.env`, tests, calidad con ruff. **Completa.**
  - Clase 2 · *Lee* (18/11/2026, `docs/Clase2.pdf`): resúmenes estructurados
    con un LLM (Pydantic + `with_structured_output`), modelo intercambiable con
    LangChain (`init_chat_model`, configurado en `LITMAR_MODELO`), un flujo
    LangGraph de revisión con verificación de citas por código, las fuentes como
    herramientas, un agente con Deep Agents (`--modo agente`, subagente buscador,
    aprobación humana) y una pestaña «Revisión» en la UI. Objetivo del día: «le
    haces a litmar una pregunta de investigación y te devuelve un informe que
    solo cita artículos reales, más el BibTeX de lo citado». El plan detallado,
    con los prompts y lo que se comprueba, está en `PROGRESS.md` («Plan de la
    Clase 2»).
  - Clase 3 · *APIs, reproducibilidad y transferencia* (19/11/2026,
    `docs/Clase3.pdf`, 35 diapositivas): tu propia API con FastAPI (rutas,
    parámetros, modelos de entrada y salida, validación, documentación
    automática), una web en HTML y JavaScript que usa esa API, Docker (imágenes,
    contenedores, capas), reproducibilidad (variables de entorno, compose,
    desarrollo dentro del contenedor) y cierre. El plan detallado, con los
    prompts y lo que se comprueba, está en `PROGRESS.md` («Plan de la Clase 3»).
  - **Principios de la Clase 3**: primero el contrato (rutas, parámetros,
    modelos de entrada y salida, códigos de error), luego el código; la API es
    un punto de entrada más, como la CLI y la UI, y reutiliza
    `buscar_en_fuentes`, `flujo.revisar` y `agente.revisar` sin duplicar lógica;
    errores con código y mensaje claro, nunca con claves (la API va sin token,
    D-24); tests con `TestClient`,
    sin red; la web solo conoce el contrato y usa rutas relativas; en Docker,
    dependencias desde `uv.lock` antes del código, sin grupo `dev`, usuario no
    root y secretos solo al arrancar (`--env-file`, `env_file:`), nunca en la
    imagen (`.dockerignore`).
  - **Principios de la Clase 2** que el código debe respetar: lo que se pueda
    hacer o verificar con código no se le deja al modelo (p. ej. comprobar que
    cada DOI citado está entre los seleccionados); flujo antes que agente; límites
    en el código (máximo de resultados, de reintentos y de pasos); errores de
    herramientas como texto, no excepciones; nada de nombres de modelo ni claves
    en el código; tests con modelos falsos, sin clave ni red.
  - Las librerías de la Clase 2 (SDK de Gemini, LangGraph, Deep Agents) cambian
    rápido: consulta su documentación actual antes de escribir código.
- **Arquitectura que el curso enseña** y hay que respetar: lógica (modelos,
  fuentes, biblioteca) separada de configuración (`.env` + `configuracion.py`) y
  de los puntos de entrada (CLI, UI y, más adelante, API). La lógica no sabe nada
  de la terminal ni de la web.

## 3. Comandos

```bash
uv sync                          # instala todo, incluido el grupo dev (pytest, ruff, streamlit)
uv run pytest                    # tests (sin red; ~351, ~13 s)
uv run ruff check --fix          # lint (reglas E, W, F, I, UP, B; línea de 100)
uv run ruff format               # formato
uv run litmar --help             # CLI
uv run litmar buscar "posidonia carbon" --fuente openalex,europepmc --desde 2020 --bibtex refs.bib
uv run litmar buscar "consulta" -n 10 --guardar biblioteca.json
uv run litmar exportar biblioteca.json --bibtex refs.bib
uv run litmar revisar "pregunta" --modo agente --aprobar   # agente; pide permiso antes de buscar
uv run litmar revisar "pregunta"  # revisión con LLM (necesita LITMAR_MODELO): informe y BibTeX
                                 # en ejemplos/revisiones/<fecha_hora_pregunta>/ (ignorado en git)
uv run litmar servir --recargar   # API (FastAPI) en http://127.0.0.1:8000, /docs
uv run litmar ui                 # interfaz web (Streamlit)
uv run litmar ui --server.headless true --server.port 8599   # sin navegador ni preguntas
```

Python ≥ 3.12 (`.python-version`: 3.12). Gestor: **uv**, backend `uv_build`,
layout `src/`. Para añadir dependencias: `uv add paquete` (nunca editar
`uv.lock` a mano); opcionales: `uv add --optional ui paquete`.

## 4. Estructura

```
src/litmar/
  __init__.py        exporta Articulo y Biblioteca; main() = entrada del comando
                     `litmar`: carga .env (python-dotenv) y llama a cli.main()
  __main__.py        `python -m litmar`
  articulo.py        Articulo (dataclass frozen+slots), normalizar_doi, apellido
  seleccion.py       puntuación compartida: relevancia y citas anualizadas
  biblioteca.py      Biblioteca: dedup por DOI, a_bibtex/exportar_bibtex, a_csv,
                     guardar/cargar JSON (guardado atómico, carga con validación)
  busqueda.py        buscar_en_fuentes(): busca en varias fuentes, junta sin
                     duplicar y recoge errores por fuente. La usan CLI y UI.
                     mensaje_de_error(): error de una fuente sin la petición
  cli.py             argparse: buscar (--fuente, --desde, --guardar, --bibtex,
                     salida en tabla), exportar, revisar (--modo flujo|agente,
                     --aprobar), ui, servir (--host, --puerto, --recargar)
  configuracion.py   FUENTES, fuentes_disponibles(), crear_fuente(nombre),
                     id_fuente()/nombre_fuente() («Europe PMC» ↔ «europepmc»)
  agente.py          agente revisor (Deep Agents): crear_agente(), Registro de lo
                     que devuelven las búsquedas, Narrador (líneas del stream),
                     ejecutar() (stream + aprobaciones), revisar() (crear +
                     ejecutar + estado_final; la usan CLI, UI y tests),
                     estado_final() con citas comprobadas;
                     MAX_PASOS/MAX_PASOS_BUSCADOR/MAX_BUSQUEDAS
  flujo.py           grafo LangGraph de revisión: EstadoRevision, crear_flujo(),
                     revisar() (ejecuta y avisa de cada paso con `mostrar`),
                     describir_paso(), informe_markdown(), enlazar_dois(),
                     citados(); límites
                     MAX_CONSULTAS/MAX_SELECCIONADOS/MAX_REESCRITURAS
  herramientas.py    @tool buscar_articulos(consulta, fuente, n) y listar_fuentes();
                     MAX_RESULTADOS = 10; errores como texto; HERRAMIENTAS
  llm.py             crear_modelo(): LITMAR_MODELO → init_chat_model, con
                     InMemoryRateLimiter y ErrorDeConfiguracion si falta algo
  resumen.py         ResumenArticulo (Pydantic) y resumir(articulo, pregunta, modelo)
                     con with_structured_output; sin resumen → None, sin llamar al modelo
  api.py             FastAPI (D-24): /salud, /fuentes, /buscar, /revisiones;
                     modelos ArticuloSalida, BusquedaSalida, RevisionEntrada,
                     RevisionSalida; validador de fuentes (→ 422). Sin token.
                     GET / sirve web/index.html del paquete
  idiomas.py         idiomas de la web e informes (es, pt-BR, en, ja), con
                     instrucciones para el modelo y rótulos del informe
  web/index.html     web (D-25): HTML+CSS+JS sin npm; usa /fuentes, /buscar y
                     /revisiones con rutas relativas; selector de idioma; conversor
                     de Markdown propio
  ui.py              Streamlit: filas(), app() con pestañas busqueda() y revision();
                     la revisión reutiliza flujo.revisar / agente.revisar
  fuentes/
    base.py          Fuente (ABC): buscar(consulta, n, *, desde=None) abstracto;
                     _admite (validez + año); _get/_get_json con reintentos
    openalex.py crossref.py europepmc.py arxiv.py pangaea.py zotero.py
docs/                diapositivas del curso (PDF) y flujo.md (diagrama del grafo;
                     un test comprueba que el Mermaid generado está al día)
ejemplos/
  resumir.py         Práctica 1 de la Clase 2: busca 3 artículos y los resume
  revisiones/        salidas de `litmar revisar`, una carpeta por ejecución (en .gitignore)
tests/
  conftest.py        fixture hacer_articulo (fábrica de Articulo válidos)
  test_*.py          uno por módulo/fuente; test_ui.py usa streamlit.testing
  datos/             respuestas reales guardadas de cada API
```

## 5. Modelo y reglas del dominio

- **`Articulo`**: `title, authors (tuple), year, doi, journal, abstract="",
  citations=None`. Inmutable. `citations=None` significa que la fuente no da
  el recuento; `0` significa que sí lo da y es cero. El DOI se normaliza (sin `https://doi.org/` ni
  `doi:`, minúsculas, debe empezar por `10.` y tener `/`) y es la **identidad**.
  DOI y al menos un autor son obligatorios: las fuentes **descartan** resultados
  sin ellos. `short_citation` → «García (2021)», «García y López (2021)»,
  «García et al. (2021)».
- **`Biblioteca`**: orden de inserción, sin duplicados; ante un DOI repetido se
  conserva **el primero**. `agregar` devuelve `bool`.
- **BibTeX**: entradas `@article`, clave apellido+año en ASCII con sufijos
  a, b, c…; título con doble llave; DOI sin escapar.
- **CSV**: mismas columnas que el JSON; autores en una celda separados por «; ».
  La UI lo descarga con BOM (`utf-8-sig`) para Excel.
- **JSON**: lista de objetos con los campos de `Articulo`; `cargar` valida tipos y
  da errores «artículo N inválido: …».

## 6. Fuentes

Todas heredan de `Fuente`, implementan `buscar(consulta, n, *, desde=None)` y
hacen sus peticiones con `self._get` / `self._get_json` (nunca `self.client.get`
directo: se perderían los reintentos). `desde` se envía como filtro a la API
cuando existe y, además, cada resultado pasa por `self._admite(articulo, desde)`,
que descarta los inválidos y los anteriores a ese año: así se devuelven `n`
artículos aunque la API interprete la fecha de otra forma. Reintentos ante
errores de red, 429 y 5xx, con espera exponencial (`backoff`), `Retry-After`
(segundos o fecha HTTP) y `max_wait` (si el servidor pide esperar más, se falla).

| Fuente (nombre en UI) | Clase | Clave / configuración | Notas |
| --- | --- | --- | --- |
| OpenAlex | `OpenAlex` | `OPENALEX_API_KEY` opcional (Bearer) | `per_page` ≤ 100; `page × per_page` ≤ 10 000; el resumen se reconstruye de `abstract_inverted_index`. `desde`: `filter=publication_year:>AÑO-1` |
| Crossref | `Crossref` | `CROSSREF_MAILTO` opcional (polite pool) | solo `journal-article`; paginación por cursor con orden explícito. `desde`: `from-pub-date:AÑO` |
| Europe PMC | `EuropePMC` | ninguna | paginación `cursorMark`; por defecto da prioridad a lo reciente. `desde`: `AND (PUB_YEAR:[AÑO TO 9999])` |
| arXiv | `Arxiv` | ninguna | Atom XML; 3 s entre páginas; DOI de respaldo `10.48550/arXiv.<id>`; citas no disponibles. `desde`: `submittedDate:[AÑO01010000 TO …]` |
| PANGAEA | `Pangaea` | ninguna | datasets; `journal="PANGAEA"`, citas no disponibles; Elasticsearch ≤ 10 000. `desde`: `range` sobre `agg-pubYear` |
| Zotero | `Zotero` | `ZOTERO_USER_ID` **o** `ZOTERO_GROUP_ID` (+ `ZOTERO_API_KEY` si es privada) | citas no disponibles; sin id no aparece en la UI. `desde`: la API no filtra, solo `_admite` |

Las variables están documentadas en `.env.example`. **Para añadir una fuente**:
subclase de `Fuente` en `fuentes/` (con `desde` y `_admite`), exportarla en
`fuentes/__init__.py`,
registrarla en `configuracion._CONSTRUCTORES`, test offline con una respuesta
real guardada en `tests/datos/`, sección en el README y, si usa claves, variable
en `.env.example`.

## 7. Convenciones

- **Idioma del código**: clases, métodos, funciones, variables, docstrings,
  comentarios y mensajes en **español**; **atributos de clase en inglés**
  (`title`, `authors`, `api_key`, `max_retries`…). Petición expresa del usuario.
  (`arxiv.py` usa nombres en inglés: deuda conocida, ver `PROGRESS.md`.)
- **Commits**: mensajes en inglés, en imperativo («Add…», «Fix…»), con cuerpo si
  hace falta explicar el porqué. Merges de PRs: «Merge pull request #N from
  usuario/rama». Terminan con la línea `Co-Authored-By` del agente si la usa.
- **Commit y push solo cuando el usuario lo pida** (suele decir «haz push»). Se
  trabaja directamente sobre `main`.
- **Tests**: obligatorios para cada cambio; **sin red** (`httpx.MockTransport`,
  `sleep` inyectado para no esperar). Respuestas reales en `tests/datos/`.
  `tests/test_desde.py` comprueba `desde` en todas las fuentes: una fuente nueva
  se añade a su lista `FUENTES`.
- **Calidad**: antes de dar algo por terminado, `uv run pytest`,
  `uv run ruff check` y `uv run ruff format --check` en verde.
- **Errores al usuario**: nunca imprimir peticiones ni cabeceras (llevan claves).
- **Documentación**: el README describe instalación, configuración, UI, CLI, uso
  desde Python y cada fuente; mantenerlo al día con cada cambio visible.

## 8. Seguridad

- **No leer nunca `.env`** ni ningún `.env.*` salvo `.env.example`. Está bloqueado
  con reglas `deny` de `Read` en `.claude/settings.json`, pero esas reglas **no**
  cubren `cat`, `grep`, etc. por Bash: tampoco se usan.
- `.gitignore` ignora `.env` y `.env.*` excepto `.env.example`.
- No enviar datos personales del usuario (correo, nombre) a servicios externos
  sin su permiso explícito.
- No hacer push a forks ajenos ni acciones destructivas sin confirmación.

## 9. Trampas conocidas

- **Reglas de permisos de Claude Code**: los globs no admiten negación
  (`!(…)`, `[!x]`, `[^x]` se toman literalmente); en macOS no distinguen
  mayúsculas (`[A-Z]` incluye `e`); `deny` gana a `allow`. Por eso la exclusión de
  `.env.example` es una cadena de rangos en minúsculas. Además, `Read` cachea el
  resultado por ruta: para probar una regla usa rutas nuevas.
- **`tests/test_pangaea.py` importa `cliente` de `test_fuentes`**: solo funciona
  con el modo de importación por defecto de pytest; con
  `--import-mode=importlib` falla la recolección.
- **`AppTest` de Streamlit**: la primera ejecución importa pandas y tarda más de
  3 s; los tests usan `default_timeout=30`.
- **Streamlit pide un correo la primera vez** si no es headless; sin terminal
  (stdin cerrado) el proceso termina. Para pruebas automáticas:
  `litmar ui --server.headless true`.
- **argparse**: `nargs=REMAINDER` en un subcomando no captura opciones que
  empiezan por `--`; por eso `litmar ui` usa `parse_known_args`.
- **`.env` solo se carga en `litmar.main()`** (la entrada del comando), no en
  `cli.main(argv)`: así los tests no leen el `.env` real.
- **`ruff format` también formatea los bloques de Python del README** (alinea
  distinto los comentarios). Es normal ver el README en el diff tras formatear.
- **Salida estructurada con Claude**: `with_structured_output` de
  `langchain-anthropic` usa por defecto `function_calling` (forzar una
  herramienta), que avisa y puede fallar en `claude-sonnet-5-5`. Pasa siempre
  `method="json_schema"`: lo admiten Anthropic y Gemini (en Gemini es el valor
  por defecto). Los modelos falsos de los tests aceptan `**opciones`.
- **`load_dotenv()` sin ruta falla con `python - <<EOF`** (stdin): `find_dotenv`
  necesita un fichero de script. En pruebas rápidas usa `load_dotenv(".env")`.
- **Docstrings de `@tool`**: con `parse_docstring=True` (formato Google) la
  primera línea, el resto y cada `Args` se convierten en la descripción que lee
  el modelo; sin él, la descripción conserva la sangría del docstring.
- **Deep Agents (0.7)**: `write_todos` ya no viene por defecto (hay que pasar
  `TodoListMiddleware`); las herramientas de ficheros se recortan pasando
  `FilesystemMiddleware(backend=…, tools=[…])` en `middleware` (en el principal y
  en el `middleware` del subagente; `read_file` es obligatoria); `task` ofrece
  siempre un subagente `general-purpose` con las herramientas del principal
  (quitarlo exige `register_harness_profile` por modelo, global). El informe
  queda en `state["files"]["/informe.md"]["content"]`.
- **Interrupciones de un subagente** (`interrupt_on` heredado): llegan dos veces
  al stream con `subgraphs=True` (en su espacio y en el principal); se atiende
  la del principal. Puede haber **varias pendientes a la vez** (el agente lanza
  buscadores en paralelo): hay que contestar a todas y reanudar con un mapa
  `Command(resume={interrupcion.id: {"decisions": [...]}, ...})`; sin ids,
  LangGraph falla con «multiple pending interrupts». Mismo `thread_id`, hace
  falta checkpointer y no se repiten llamadas al modelo.
- **`ModelCallLimitMiddleware(exit_behavior="end")`** añade su mensaje («Model
  call limits exceeded…») desde el nodo `ModelCallLimitMiddleware.before_model`,
  no desde `model`. Con aprobaciones cada reanudación es un *run* nuevo: para el
  principal se usa `thread_limit`.
- **Modelos falsos para agentes**: un `BaseChatModel` con `_generate` que saca
  mensajes de un guion y `bind_tools` que devuelve un envoltorio (ver
  `tests/test_agente.py`). El principal y el subagente comparten el guion.
- **Streamlit: la `key` de un formulario no puede ser también una clave de
  `st.session_state`** (`StreamlitWidgetAlreadyInstantiatedError`). Por eso el
  formulario es `"revision"` y el resultado, `resultado_revision`.
- **`AppTest`**: `st.status(...)` y sus `.text()` aparecen en `app.text`; las
  pestañas no cambian el orden de los widgets (los de «Búsqueda» van primero:
  `multiselect[0]`, los de «Revisión», `multiselect[1]`).
- **FastAPI no valida los valores por defecto**: un `AfterValidator` (p. ej. el
  que convierte «openalex» en «OpenAlex») no se aplica al valor por defecto de un
  `Query` o de un campo Pydantic. Hace falta `validate_default=True`; si no, el
  nombre sin convertir llega a `crear_fuente` y la fuente «falla».
- **`Retry-After: 0`** es válido: comprobar con `is None`, no con `or`.
- **`Biblioteca.guardar`** deja el JSON con permisos `0600` (lo crea
  `NamedTemporaryFile`). Conocido, pendiente.
- **Merges de PRs desde local**: hacer push a `main` de una rama que contiene el
  commit de la PR hace que GitHub la marque como MERGED. Para conflictos, rama
  `integrar-N`, resolver, tests, `merge --ff-only` en `main`, push.
- **Acciones que el sistema de permisos de Claude Code ha bloqueado** (modo
  automático): hacer push a la rama de un fork ajeno y borrar ficheros de la
  memoria privada del agente. No intentes rodearlo: explica qué querías hacer y
  deja que el usuario decida.

## 10. Cómo trabaja el usuario

- **Es el profesor del curso** y usa estas sesiones para preparar y dar las
  clases. Varios encargos han sido **copia literal de los prompts de las
  diapositivas** (Articulo y Biblioteca, Fuente y OpenAlex, la interfaz
  Streamlit). Si un encargo coincide con una diapositiva de `docs/`, léela: la
  columna «En qué fijarse» dice qué se va a comprobar en clase, y el resultado
  debe superarlo (p. ej. «¿Qué pasa si una fuente falla?», «¿Alguna clave visible
  en la interfaz?»).
- **Escribe en español, con mensajes cortos** y a veces con erratas. «sí», «si»,
  «adelante», «sii» significan «hazlo». Si algo es ambiguo de verdad (p. ej.
  «haz a y b» cuando no había nada marcado con a y b), pregunta antes.
- **Pide explicación antes de código** en los encargos grandes («explícame el
  diseño antes»). Encaja con el método del curso: primero el plan, luego el
  código.
- **Hace preguntas de concepto** (qué es `staticmethod`, uv frente a venv, qué es
  `pyproject.toml`) para explicarlas en clase: respuestas didácticas, breves y con
  ejemplos del propio proyecto.
- **Le gusta que le guíen paso a paso** en tareas con efectos hacia fuera (PRs,
  comentarios, merges): el agente propone, explica el porqué y pregunta antes de
  comentar, cerrar, fusionar o hacer push.
- **Al terminar**, un resumen corto: qué se hizo, cómo se comprobó (tests, prueba
  real) y qué queda pendiente o requiere su decisión.

## 11. Revisar e integrar PRs de alumnos

1. `gh pr list` y `gh pr view N` (autor, rama, descripción). Comprueba si duplica
   una fuente o funcionalidad que ya existe (D-6).
2. Trae la rama: `git fetch origin pull/N/head:pr-N`. Lee el diff completo
   (`git diff main...pr-N`), ejecuta los tests **en su rama** y una **fusión de
   prueba** con `main` (rama `integrar-N`): conflictos, tests, ruff y, si toca
   una API, una prueba real.
3. Informa al usuario: puntos fuertes, problemas (bloqueantes o no) y una
   recomendación. **Espera su visto bueno** antes de comentar, cerrar o fusionar.
4. Para integrar: en `integrar-N`, `git merge --no-ff pr-N` con el mensaje
   «Merge pull request #N from usuario/rama», resuelve conflictos, tests y ruff en
   verde, `git switch main && git merge --ff-only integrar-N`, push. GitHub marca
   la PR como MERGED. Borra `pr-N` e `integrar-N`.
5. Comenta en la PR (`gh pr comment N`): agradecimiento, qué se cambió al
   integrar y mejoras propuestas para una PR de seguimiento. Tono didáctico.
   Anota esas propuestas en «Pendiente de terceros» de `PROGRESS.md`.
6. Para PRs duplicadas: ciérralas (`gh pr close N --comment …`) explicando por
   qué se eligió otra e invitando a aportar sus mejoras sobre la existente.
7. Si la PR toca `PROGRESS.md`, sus cambios describen la máquina del alumno
   (rama local, `stash`, commit de su `main`): al resolver conflictos, deja un
   solo «Estado actual» cierto para el repositorio y quita lo que solo valía allí.
8. Tras el formateo con ruff (D-13), una PR basada en el `main` anterior puede
   chocar solo por formato: pide al alumno `uv run ruff format`, o fórmatealo tú
   al integrar.

