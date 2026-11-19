# DECISIONS — decisiones de diseño y de proceso

Por qué litmar es como es, para no volver a discutir lo ya decidido. Cada entrada:
fecha, decisión, motivo y alternativas descartadas. No se borran: si una decisión
cambia, se marca **Sustituida por D-N** y se añade la nueva al final.

---

### D-1 · uv, layout `src/` y `uv_build` — 2026-11-17
uv gestiona entorno, dependencias y lockfile con un solo comando y es mucho más
rápido que venv + pip. El layout `src/` evita importar por accidente el código
sin instalar. El proyecto sigue siendo instalable con `pip install .`.

### D-2 · Idioma: español, salvo atributos de clase en inglés — 2026-11-17
Petición del usuario. Clases, métodos, funciones, variables, docstrings y
mensajes en español; atributos (`title`, `authors`, `max_retries`…) en inglés.
Commits en inglés.

### D-3 · El DOI es la identidad de un artículo — 2026-11-17
`Articulo` exige DOI (normalizado) y al menos un autor; `Biblioteca` deduplica
por DOI y conserva el primero. Las fuentes descartan lo que no cumpla. Así la
deduplicación entre fuentes es trivial y fiable. Descartado: deduplicar por
título (frágil) o permitir artículos sin DOI.

### D-4 · Reintentos en la clase base `Fuente` — 2026-11-17
Todas las fuentes comparten la misma política: reintento ante errores de red,
429 y 5xx, espera exponencial, `Retry-After` y `max_wait` para no esperar horas
cuando se agota un cupo diario. `sleep` y `client` son inyectables para tests.

### D-5 · Tests sin red con respuestas reales guardadas — 2026-11-17
`httpx.MockTransport` + JSON/XML reales en `tests/datos/`. Los tests son
deterministas, rápidos y no gastan cupo de las APIs.

### D-6 · Una fuente por servicio; ante PRs duplicadas se elige una — 2026-11-17
Con varias PRs para el mismo servicio se acepta la más completa y correcta, y se
cierran las demás con un comentario que explica el motivo e invita a aportar sus
mejoras sobre la elegida. Las PRs se integran desde local con un commit «Merge
pull request #N from usuario/rama» y push a `main`; GitHub las marca MERGED.

### D-7 · `.env` bloqueado para el agente — 2026-11-17
Reglas `deny` de `Read` en `.claude/settings.json` para `.env` y `.env.*`, con
excepción de `.env.example` construida con rangos de caracteres (los globs no
admiten negación). Las reglas no cubren Bash: el agente tampoco usa `cat` con él.

### D-8 · Configuración por variables de entorno y `.env` — 2026-11-17
Claves y datos de fuentes en variables (`OPENALEX_API_KEY`, `CROSSREF_MAILTO`,
`ZOTERO_*`), cargadas desde `.env` con python-dotenv **solo en la entrada del
comando `litmar`** (para que los tests no lean el `.env` real). Las variables ya
definidas tienen prioridad. `configuracion.py` es el único sitio que traduce
variables en fuentes. Descartado: `uv run --env-file` (no sirve con pip).

### D-9 · Streamlit como dependencia opcional (`ui`) — 2026-11-17
Streamlit arrastra pandas, pyarrow y más; quien use la librería o la CLI no lo
necesita. Se instala con `uv sync --extra ui` o `pip install 'litmar[ui]'`, y
está también en el grupo dev. `litmar ui` lanza `streamlit run` con el mismo
intérprete, reenvía las opciones extra y desactiva las estadísticas de uso.

### D-10 · Memoria del proyecto en el repositorio — 2026-11-17
`AGENTS.md` (estable), `PROGRESS.md` (vivo) y `DECISIONS.md` (este), versionados
en git y compartidos con los colaboradores. El agente actualiza `PROGRESS.md` por
su cuenta al terminar cada tarea, y los hooks de Claude Code inyectan el estado
al empezar y recuerdan anotar al terminar. Descartado: memoria privada del
agente (no la ven otros agentes ni personas, y se pierde al cambiar de máquina).

### D-11 · `desde` como parámetro de `Fuente.buscar`, filtrado en la API y en local — 2026-11-17
Para `litmar buscar --desde AÑO` (demo de la Clase 1). Cada fuente pasa el año a
su API (comprobado contra las APIs reales) y además descarta con `_admite` lo
anterior, porque cada API fecha distinto (arXiv usa la primera versión; Zotero
no filtra). Descartado: filtrar solo los resultados ya descargados, porque con
`-n 5` podrían quedar menos de 5.

### D-12 · Búsqueda multifuente compartida en `busqueda.py` — 2026-11-17
CLI y UI usan `buscar_en_fuentes`: si una fuente falla se sigue con las demás y
se devuelven los errores (sin cabeceras ni peticiones). En la CLI, si fallan
todas es un error (código 1, no se guarda nada); si falla alguna, solo un aviso.

### D-13 · ruff con línea de 100 y reglas E, W, F, I, UP, B — 2026-11-17
Lo enseña la Clase 1. 100 en lugar de 88 porque el código ya estaba escrito así y
evita partir líneas sin ganar legibilidad. Al adoptarlo se formateó todo el
proyecto de una vez, en el mismo commit que `--fuente`/`--desde`.

### D-14 · Variables del LLM: `LITMAR_MODELO` + clave del proveedor; se mantiene `CROSSREF_MAILTO` — 2026-11-17
Lo fijan las diapositivas de la Clase 2: `LITMAR_MODELO=proveedor:modelo` (p. ej.
`google_genai:gemini-3.8-flash` o `anthropic:claude-sonnet-5-5`) y la clave con
el nombre estándar de cada proveedor (`GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`),
que es el que leen las librerías de LangChain. Sustituye a la idea de
`GEMINI_API_KEY` de la Clase 1. Las diapositivas también nombran
`CROSSREF_MAILTO`, así que no se renombra a `LITMAR_EMAIL`.

### D-15 · LangChain y los dos proveedores como dependencias normales — 2026-11-18
`langchain` (por `init_chat_model`), `langchain-core`, `langchain-google-genai`
y `langchain-anthropic` van en `dependencies`, no en un extra opcional como
Streamlit (D-9): resumir y revisar son el centro de la Clase 2 y los alumnos
deben poder usar Gemini o Claude tras `uv sync`, sin pasos extra. Otro proveedor
se añade con `uv add langchain-<proveedor>` y su variable de clave en
`llm._CLAVES` (si no está, `crear_modelo` deja que LangChain lo compruebe).

### D-16 · Límite de llamadas por minuto en el modelo, configurable — 2026-11-18
`crear_modelo()` pasa un `InMemoryRateLimiter` de LangChain a `init_chat_model`:
10 llamadas por minuto por defecto (plan gratuito de Gemini), cambiable con
`LITMAR_LLAMADAS_POR_MINUTO` (0 = sin límite, p. ej. con una clave de pago).
`max_bucket_size=1` espacia las llamadas en vez de permitir ráfagas. La clave se
comprueba antes de crear el modelo para dar un error que diga qué línea añadir
al `.env`. Como D-8, `llm.py` lee el entorno y no carga `.env`: lo hace el
comando `litmar`; los scripts propios llaman a `load_dotenv()`.

### D-17 · Flujo de revisión: «los N mejores» son los más citados — 2026-11-18 (sustituida por D-23)
`filtrar` se queda con los artículos con resumen y los ordena por citas. Es
fácil de explicar y de comprobar, aunque favorece lo antiguo (en la prueba real
entraron revisiones generales sobre olas de calor). Cambiar el criterio es el
ejercicio natural de la Práctica 2. Descartado de momento: por año, o el orden de
relevancia de cada API. Lo eligió el usuario.

### D-18 · Citas inventadas tras agotar las reescrituras: se marcan — 2026-11-18
Tras `MAX_REESCRITURAS` (2), `verificar_citas` sustituye cada DOI que no está
entre los resumidos por «[cita no verificada]» y añade un aviso. Así ningún DOI
sin comprobar llega al informe ni al BibTeX. Descartado: guardar el informe tal
cual con un aviso, o fallar sin guardar nada. «Seleccionados» son los artículos
que el modelo vio en la síntesis, no todos los candidatos puntuados. Las
referencias del informe las genera el código a partir de los DOI verificados.
Lo eligió el usuario. Los campos del estado (`EstadoRevision`) van en inglés por
D-2, aunque la diapositiva diga «pregunta, artículos…».

### D-19 · Cada revisión, en su carpeta de `ejemplos/revisiones/`, fuera de git — 2026-11-18
Petición del usuario: las salidas de `litmar revisar` no se mezclan en el
directorio de trabajo. Cada ejecución crea
`ejemplos/revisiones/AAAA-MM-DD_HHMM_<pregunta-sin-acentos>/` con `revision.md`
y `revision.bib` (nombre recortado a 50 caracteres sin partir palabras; si ya
existe, `-2`, `-3`…). La carpeta se crea al final, para que una revisión que
falla no deje carpetas vacías. `ejemplos/revisiones/` va en `.gitignore`: cada
alumno tiene las suyas y no aparecen en sus PRs (una de muestra se puede añadir
con `git add -f`). `--informe` y `--bibtex` siguen permitiendo otra ruta. La
ruta es relativa al directorio desde el que se ejecuta `litmar`. Descartado:
nombrar solo por pregunta (se pisan) o solo por fecha (no dice de qué trata).

### D-20 · Una herramienta de búsqueda para todas las fuentes, errores como texto — 2026-11-18
Diapositiva 28. `buscar_articulos(consulta, fuente, n)` en vez de una
herramienta por fuente: el modelo elige la fuente con un parámetro y una fuente
nueva que llegue por PR queda disponible sin tocar las herramientas
(`listar_fuentes` usa `fuentes_disponibles`; la descripción para el modelo sale
de `herramientas.DESCRIPCIONES`, y si falta dice «sin descripción»). `fuente`
es `str` y se valida en el código (no un `Literal`), para que un nombre
inválido vuelva al modelo como texto con la lista de válidas en lugar de un
error de validación. Cualquier excepción de la fuente se convierte en texto con
`busqueda.mensaje_de_error`, que nunca incluye la petición (la URL puede llevar
`CROSSREF_MAILTO` o claves). Límite de 10 y resumen recortado a 400 caracteres
en el código.

### D-21 · Agente revisor: herramientas mínimas, registro de búsquedas y límites — 2026-11-18
Diapositivas 36-39. `--modo agente` usa `create_deep_agent` con:
- **Agente principal** con `write_todos` (`TodoListMiddleware`), `task`,
  `listar_fuentes` y solo `ls`/`read_file`/`write_file` sobre un `StateBackend`
  (ficheros virtuales). No busca él: lo delega en el subagente `buscador`
  (`buscar_articulos`, `listar_fuentes`, `read_file`), para que su contexto no
  se llene de resultados (diapositiva 37).
- **Citas comprobadas con código**: las herramientas del agente envuelven las de
  `herramientas.py` (mismo nombre, descripción y argumentos, vía
  `herramientas.buscar`) y guardan en un `Registro` cada artículo devuelto. Al
  final, los DOI citados que no estén en el registro se marcan (como D-18). No
  hay bucle de reescritura: el agente no se vuelve a llamar.
- **Mismo formato que el flujo**: `estado_final` devuelve un estado con las
  claves del flujo y se reutilizan `informe_markdown` y `citados`.
- **Límites**: `ModelCallLimitMiddleware` (25 pasos el principal con
  `thread_limit`, 8 el buscador por encargo) y 12 búsquedas en total dentro de
  la herramienta. Al llegar al límite, el informe añade «Hasta dónde llegó» con
  la lista de tareas (diapositiva 42).
- **`--aprobar`**: `interrupt_on` para `buscar_articulos` (heredado por el
  buscador), decisiones aprobar/editar/rechazar desde la terminal; sin terminal
  (EOF) se rechaza. Requiere `MemorySaver`.
- Se acepta el subagente `general-purpose` que añade Deep Agents (no puede
  buscar) antes que un perfil global por modelo. `--fuente` limita las fuentes
  en el código; `-n` es el máximo de artículos que elige el agente.

### D-22 · La revisión en la UI reutiliza `flujo.revisar` y `agente.revisar` — 2026-11-18
Diapositiva 40. Los bucles que imprimían en la CLI (`_con_flujo`, `_con_agente`)
pasan a `flujo.revisar()` y `agente.revisar()`, que reciben una función
`mostrar(linea)`: la CLI pasa `print` y la UI, `st.status(...).text`, que
escribe cada paso en cuanto llega. La salida de la terminal no cambia. La UI no
ofrece `--aprobar` (una pausa a mitad de un script de Streamlit exigiría otro
diseño: guardar el grafo en la sesión y reanudar en otra ejecución); queda para
la terminal. Si falta la configuración del modelo, aviso con la línea del `.env`
y botón desactivado. `MAX_ARTICULOS_REVISION` repite `MAX_SELECCIONADOS` para
no cargar LangGraph al abrir la UI; un test comprueba que coinciden.

### D-23 · Selección combinada con relevancia y citas anualizadas — 2026-11-18
La relevancia para la pregunta (1–5) pesa 70 % y la puntuación de citas ajustada
30 %. Para esta implementación se adopta esa proporción para mantener la
relevancia como señal principal. Para el ajuste,
`tasa = citas / max(1, año_actual - año_publicación + 1)`
y `puntuación_citas = 1 + 4 × tasa / (1 + tasa)`, en escala 1–5. Un `citations`
igual a `None` significa que la fuente no proporciona el dato: en ese caso se
usa solo la relevancia y se avisa. `0` sigue significando cero citas conocidas.
El flujo calcula la puntuación con código; en modo agente, la herramienta expone
la tasa y el ajuste, y el prompt pide aplicar la misma regla. Se sustituye
D-17, que ordenaba por citas totales.

### D-24 · Contrato de la API (FastAPI) — 2026-11-19
`src/litmar/api.py`: `GET /salud`, `GET /fuentes`, `GET /buscar` y
`POST /revisiones`, con `buscar_en_fuentes`, `flujo.revisar` y `agente.revisar`
(sin lógica nueva). Lo eligió el usuario al ver el contrato:
- **`/buscar` devuelve un objeto** `{query, articles, errors, failed}`, no una
  lista como en la demo de la diapositiva 10: con una lista no hay dónde decir
  que una fuente falló. 200 si responde alguna fuente; **502** si fallan todas.
- **Sin token**, aunque la diapositiva 9 lo pide opcional: la API es para el
  ordenador propio o una red de confianza. El README avisa de que quien llame a
  `/revisiones` gasta la clave del modelo. Si hiciera falta, la idea era
  `LITMAR_API_TOKEN` + `Authorization: Bearer`, comparado con
  `secrets.compare_digest`.
- **Campos JSON en inglés** (como `Articulo` y D-2) y parámetros de la URL en
  español (`consulta`, `fuente`, `n`, `desde`, como la CLI).
- Errores: **422** datos inválidos (también una fuente desconocida o Zotero sin
  configurar, comprobado por un validador de Pydantic); **503** si falta el
  modelo (mensaje de `ErrorDeConfiguracion`); **502** si el modelo falla, solo
  con el tipo de error, porque el mensaje del proveedor podría llevar la petición.
- `/revisiones` es **síncrona** (`def`, FastAPI la ejecuta en otro hilo) y
  responde 200, no 201: no crea nada consultable. El modo agente va sin
  aprobaciones. No guarda nada en disco.
- `fastapi` y `uvicorn` son dependencias principales, no un extra, para que la
  imagen de Docker las tenga sin el grupo `dev`.

### D-25 · Web de litmar: un fichero, pregunta propia y Markdown sin librerías — 2026-11-19
`src/litmar/web/index.html`, servida por la API en `GET /` (fuera de `/docs`:
no es parte del contrato) y leída del paquete con `importlib.resources`, para
que funcione igual instalada o en Docker. Solo usa `/fuentes`, `/buscar` y
`/revisiones`, con rutas relativas; un test lo comprueba. Lo eligió el usuario:
- **La revisión tiene su propio campo de pregunta** (con modo y número de
  artículos) y reutiliza las fuentes y el año del formulario de búsqueda, como
  la pestaña «Revisión» de la UI.
- **El informe se muestra como Markdown renderizado** con un conversor propio
  de unas 100 líneas (títulos, párrafos, listas anidadas, tablas, citas, código,
  énfasis, enlaces y `[doi:…]`). Descartado: una librería desde una CDN (la web
  dejaría de funcionar sin internet y habría que sanear el HTML) y el texto tal
  cual en un `<pre>`. El conversor escapa todo el texto antes de dar formato y
  solo crea enlaces `http(s)`: el informe no puede meter HTML en la página.
- Los datos de la API se pintan con `textContent`, nunca con `innerHTML`; el
  BibTeX y el informe se descargan con un `Blob`, sin otra petición. Los 422 se
  traducen campo a campo; sin JSON (p. ej. un 502 de nginx), «HTTP N».

### D-26 · Idioma seleccionado para la web y el informe — 2026-11-19
La web permite español, portugués de Brasil, inglés y japonés. Envía el idioma
seleccionado como `language` en `POST /revisiones` (`es`, `pt-BR`, `en`, `ja`);
se conserva español como valor por defecto para no cambiar a los clientes
existentes. El idioma se aplica a los prompts de resumen y síntesis (flujo) o al
prompt del agente, y a los rótulos que genera el código en el informe. Los
títulos y metadatos de los artículos no se traducen. Así no se hace una segunda
llamada al modelo para traducir resultados ni se alteran datos bibliográficos.
