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

### D-15 · Un artículo sin resumen no se envía al modelo — 2026-11-18
`resumir` lanza `ValueError` si el resumen está vacío o solo contiene espacios,
antes de invocar el modelo. Así el contrato de éxito siempre devuelve un
`ResumenArticulo`; se descarta devolver `None`, que obligaría a tratar una
ausencia esperable como una salida alternativa al objeto solicitado.

### D-16 · Limitador local compartido para Gemini — 2026-11-18
`crear_modelo` comparte un `InMemoryRateLimiter` entre los modelos Gemini del
proceso y limita a 10 solicitudes por minuto, sin ráfagas. Las cuotas reales de
Google varían según el modelo y el proyecto y se aplican también al uso externo;
el límite local reduce el ritmo de litmar, pero no sustituye la cuota del
proveedor ni coordina varios procesos.
