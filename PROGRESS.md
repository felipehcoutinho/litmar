# PROGRESS — estado y registro de litmar

Memoria viva del proyecto. Cómo se usa y cuándo se actualiza: `AGENTS.md`, §1.
«Estado actual» y «Próximos pasos» se reescriben para que siempre sean ciertos;
el registro solo crece (entradas nuevas arriba).

## Estado actual

_Actualizado: 2026-11-18._

- **Git**: la rama de trabajo `day2` parte del último `main` sincronizado con
  `origin/main` (`2b5422e`). El resumen estructurado y la fábrica de modelos de
  la Clase 2 están en el árbol de trabajo, aún sin commit.
- **Curso**: Clase 1 (*Busca*, 17/11/2026) completa respecto a las
  diapositivas. La Clase 2 (*Lee*, 18/11/2026) está en curso: ya está
  implementados el resumen estructurado, la fábrica de modelos y el ejemplo de
  resumen; quedan el flujo de revisión, las herramientas, el agente y la UI.
- **Calidad**: 216 tests pasan sin red; `ruff check` y `ruff format --check`
  están en verde.
- **PRs abiertas**: ninguna.
- **Funciona**:
  - modelo `Articulo` y `Biblioteca` (dedup por DOI, BibTeX, CSV, JSON);
  - `resumir(articulo, pregunta, modelo)`, que devuelve un `ResumenArticulo`
    Pydantic con relevancia validada entre 1 y 5 y no llama al modelo si falta
    el resumen;
  - `litmar.llm.crear_modelo()`, que lee `LITMAR_MODELO`, valida la clave del
    proveedor y usa `init_chat_model`; Gemini queda limitado a 10 solicitudes
    por minuto dentro del proceso;
  - `ejemplos/resumir.py`, que busca candidatos en OpenAlex y Europe PMC, y
    resume tres artículos que tengan resumen;
  - seis fuentes: OpenAlex, Crossref, Europe PMC, arXiv, PANGAEA, Zotero; todas
    admiten `desde` (año mínimo);
  - CLI: `litmar buscar "…" --fuente openalex,europepmc --desde 2020 --bibtex
    refs.bib --guardar biblioteca.json`, con salida en tabla; `litmar exportar`;
    `litmar ui`;
  - interfaz web con Streamlit: búsqueda en varias fuentes, tabla y descargas
    BibTeX/CSV;
  - configuración por `.env` (plantilla en `.env.example`; todo opcional salvo
    Zotero).

## Próximos pasos

Por orden de prioridad sugerido:

0. [ ] **Comprobar el arnés de memoria**. `SessionStart` **funciona**: el
   18/11/2026, al reanudar la sesión, inyectó el estado de este fichero y de git.
   Falta ver en una sesión real que `Stop` pide anotar el progreso cuando hay
   trabajo sin registrar (los casos se probaron a mano con un repo de prueba).
1. [ ] **Clase 2**: continuar el plan de abajo con el flujo de revisión; después
   añadir herramientas, agente y UI.
2. [ ] **Permisos del JSON**: `Biblioteca.guardar` deja `0600`; aplicar la umask
   con `os.chmod` antes de `os.replace`. Propuesto en la PR #10.
3. [ ] **Mover el helper `cliente` de `tests/test_fuentes.py` a `conftest.py`**,
   para que `test_pangaea.py` no importe de otro fichero de tests.
4. [ ] **`pyproject.toml`**: cambiar `description = "Add your description here"`.
5. [ ] **«Desde el año» en la UI**: `buscar_en_fuentes` ya admite `desde`; falta
   el campo en `ui.py`.
6. [ ] **Ideas para la UI** (sin pedir aún): guardar/cargar la biblioteca JSON,
   filtrar u ordenar resultados, mostrar de qué fuente viene cada artículo.

## Plan de la Clase 2 (de `docs/Clase2.pdf`)

Los encargos que se lanzan «en directo», en orden. Cada uno trae en la
diapositiva una columna «En qué fijarse»: el resultado debe superarla. Consultar
la documentación actual de LangChain, LangGraph y deepagents antes de programar
(cambian rápido) y proponer plan antes de código.

1. [x] **`.env`** (diapositiva 4): `LITMAR_MODELO=google_genai:gemini-3.8-flash`
   + `GOOGLE_API_KEY`, o `anthropic:claude-sonnet-5-5` + `ANTHROPIC_API_KEY`. El
   plan gratuito de Gemini tiene límites por minuto (429) y Google puede usar lo
   enviado: solo datos públicos. Variables y ejemplos añadidos a `.env.example`.
2. [x] **Resumen estructurado**: `resumir(articulo, pregunta, modelo)` → objeto
   Pydantic `ResumenArticulo` (objetivo, método, hallazgos, relevancia 1-5
   respecto a la pregunta, limitaciones) con `with_structured_output`. Cada
   campo con descripción (el modelo la lee). Sin resumen → no llamar al modelo.
   Implementado en `src/litmar/resumen.py`; si el resumen falta o está vacío,
   lanza `ValueError` sin invocar el modelo (D-15). Test con modelo falso, sin
   clave ni red.
3. [x] **Modelo intercambiable**: `src/litmar/llm.py` con `crear_modelo()` que lee
   `LITMAR_MODELO` y usa `init_chat_model`; límite de llamadas por minuto para el
   plan gratuito; si falta la clave, error claro que diga qué poner en el `.env`.
   Implementado con límite local compartido de 10 solicitudes/minuto para Gemini
   (D-16); las cuotas del proveedor varían por proyecto/modelo y no se comparten
   entre procesos. Si falta la clave, el error indica qué variable añadir al
   `.env`. Ningún nombre de modelo ni clave secreta en el código.
4. [x] **Práctica 1** de los alumnos: `ejemplos/resumir.py` busca candidatos en
   OpenAlex y Europe PMC y resume los tres primeros con abstract; si no hay tres,
   termina con un mensaje claro. Test de orquestación sin red ni clave.
5. [ ] **Flujo LangGraph** (`src/litmar/flujo.py`): estado `TypedDict`
   (`EstadoRevision`: pregunta, artículos, resúmenes, informe…); nodos
   `planificar` (LLM: pregunta → 2-3 búsquedas), `buscar` y `filtrar` (código:
   fuentes y Biblioteca; con resumen, sin duplicados, los N mejores),
   `resumir_articulos` (con `resumir()`), `sintetizar` (LLM, cita por DOI) y
   `verificar_citas` (código: cada DOI citado está entre los seleccionados; si
   no, vuelve a `sintetizar`, máximo 2 veces). Comando `litmar revisar
   "pregunta" --modo flujo` que muestra cada paso (ver demo, diapositiva 21) y
   guarda el informe y el BibTeX de lo citado. Primero plan y diagrama Mermaid.
6. [ ] **Herramientas** (`src/litmar/herramientas.py`): `buscar_articulos(consulta,
   fuente, n)` (reutiliza `crear_fuente`) y `listar_fuentes` (usa
   `fuentes_disponibles`), con `@tool` de LangChain. Máximo 10 en el código;
   errores como mensaje; devuelven título, año, DOI, citas y resumen recortado;
   docstrings pensados para el modelo; avisar de que PANGAEA da datos, no
   artículos. Tests sin red.
7. [ ] **Votación en clase** (una de tres): Zotero por MCP
   (`github.com/Sapere-IA/zotero-mcp`, solo herramientas de lectura, arranque en
   el `.env`; el MCP solo para PDFs y notas, sin duplicar la búsqueda), Semantic
   Scholar como herramienta de citas, o una fuente de CSV/BD local del grupo.
8. [ ] **Agente con Deep Agents**: `litmar revisar … --modo agente` con
   `create_deep_agent` y `herramientas.py`; instrucciones: planificar con lista
   de tareas, buscar en varias fuentes, citar solo DOIs que den las herramientas
   y decir lo que no encontró. Mismo formato de informe y BibTeX que el flujo.
   Subagente buscador. `--aprobar` con `interrupt_on` para pedir permiso antes de
   buscar. Límite de pasos (si se alcanza, escribir hasta dónde llegó) con test de
   modelo falso.
9. [ ] **Pestaña «Revisión» en la UI**: pregunta, modo flujo/agente, fuentes y
   número de artículos; pasos en vivo; informe con los DOI como enlaces; mensaje
   claro si falta la clave. Reutilizar las funciones de revisión (refactor
   mínimo si imprimen por pantalla) sin romper la terminal.
10. [ ] **Para la Clase 3**: los alumnos deben comprobar `docker run hello-world`.

## Cabos sueltos

- **Memoria privada del agente duplicada**: en la máquina del usuario queda
  `~/.claude/projects/-Users-presindev-dev-scratch-litmar/memory/atributos-en-ingles.md`
  (y su línea en `MEMORY.md` de esa carpeta) con la convención de atributos en
  inglés, que ya está en `AGENTS.md` §7. El sistema de permisos impidió borrarla;
  puede borrarla el usuario. No molesta, pero no hay que mantenerla.
- **El PDF de `docs/` incluye el correo y el LinkedIn del usuario** (portada y
  cierre); el repositorio es público. El usuario lo subió a sabiendas.

## Pendiente de terceros

Mejoras pedidas a colaboradores en comentarios de PR. Si llega una PR, revisarla
contra esto.

- **arXiv** (@ddietor, comentario en #11): aplicar la pausa de 3 s también a los
  reintentos (`backoff=3.0`) y pasar los nombres a español.
- **Zotero** (@acanari, #12 cerrada por duplicada): se le invitó a aportar sus
  mejoras sobre la fuente existente: DOI desde el campo «Extra» y usar
  `/items/top`.
- **Throttle genérico** (@rsune8, #9 cerrada por duplicada): se le invitó a
  proponer su hook `_antes_de_peticion` en `Fuente`.

## Registro de sesiones

### 2026-11-18 — Ejemplo de resumen sobre bacteriófagos de Nitrospira

- Creado `ejemplos/resumir.py`: busca candidatos en OpenAlex y Europe PMC,
  selecciona tres con resumen y los procesa con `crear_modelo()` y `resumir()`.
  Si no hay tres, falla antes de crear el modelo; al ejecutarse carga `.env`.
- Testea la orquestación con búsqueda y resumen simulados, sin red ni claves.
- Verificación: 216 tests pasan; `ruff check`, `ruff format --check`,
  `git diff --check` y `uv lock --check` pasan. No se hizo una búsqueda real.

### 2026-11-18 — Fábrica de modelos intercambiables

- Añadido `src/litmar/llm.py`: `crear_modelo()` lee `LITMAR_MODELO`, valida el
  proveedor (`google_genai` o `anthropic`) y su variable de clave antes de usar
  `init_chat_model`. Los errores de configuración indican qué añadir al `.env`.
- Gemini usa un limitador de 10 solicitudes/minuto compartido en el proceso
  (D-16). La documentación advierte que la cuota de Google depende del modelo y
  del proyecto y no se coordina entre procesos.
- Añadidas las variables y ejemplos a `.env.example`, dependencias LangChain y
  las integraciones Google/Anthropic, documentación en README y descripción del
  módulo en AGENTS.md.
- Tests con `init_chat_model` simulado: 214 tests pasan; `ruff check`,
  `ruff format --check` y `uv lock --check` pasan. Se instanciaron ambos
  proveedores con claves falsas, sin llamadas de red.

### 2026-11-18 — Resumen estructurado para la Clase 2

- Añadidos `ResumenArticulo` (Pydantic) y `resumir(articulo, pregunta, modelo)`
  con `with_structured_output`; relevancia validada en 1-5 y campos descritos
  para el modelo.
- Sin resumen (incluidos espacios en blanco), se lanza `ValueError` antes de
  llamar al modelo. El test usa un modelo falso y no usa clave ni red (D-15).
- Añadidas las dependencias `pydantic` y `langchain-core`, exportación desde
  `litmar`, documentación del contrato en README y tests.
- Verificación: 208 tests pasan; `ruff check` y `ruff format --check` pasan.
- La Clase 2 está en curso; falta continuar con la configuración del modelo y
  los pasos restantes del plan.

### 2026-11-18 — Sesión 2: comprobación de los hooks

- El hook `SessionStart` funciona en una sesión real (al reanudar inyectó el
  estado de `PROGRESS.md` y de git). Paso 0 actualizado.
- Dudas del usuario sobre `Stop`: se ejecuta al final de **cada turno** (no al
  salir, ni con Esc, ni si se apaga el ordenador; para la salida existe
  `SessionEnd`, que no puede pedir nada al agente). Cuesta 0 tokens cuando deja
  terminar; si bloquea, ~100 tokens más la edición de `PROGRESS.md`, una vez por
  turno. Se le ofreció una versión más silenciosa (ignorar commits ya hechos);
  de momento se queda como está.
- Sin cambios de código. La Clase 2 sigue sin empezar.

### 2026-11-17 — Sesión 1 (cierre 2): diapositivas de la Clase 2

- El usuario añadió `docs/Clase2.pdf`. De ella salen: el «Plan de la Clase 2»
  de este fichero, la hoja de ruta y los principios de `AGENTS.md` §2, y D-14
  (variables `LITMAR_MODELO` + clave del proveedor; `CROSSREF_MAILTO` se queda),
  que resuelve la duda pendiente sobre `LITMAR_EMAIL`.
- No se ha escrito código de la Clase 2. Queda por preguntar al usuario si se
  construye ya o en directo en clase.

### 2026-11-17 — Sesión 1 (cierre): memoria lista para la siguiente sesión

- Repaso completo de los ficheros de memoria para que una sesión con contexto
  vacío pueda retomar: calendario del curso (`AGENTS.md` §2), cómo trabaja el
  usuario (§10), procedimiento para revisar PRs de alumnos (§11), acciones que
  bloquea el sistema de permisos (§9), «Cabos sueltos» y el paso 0 (comprobar los
  hooks) en este fichero.
- Estado al cerrar: `main` sincronizado con `origin/main`, árbol limpio, 204
  tests y ruff en verde, ninguna PR abierta.

### 2026-11-17 — Sesión 1 (cont.): CLI de la demo y ruff

- **CLI como en la diapositiva 8 de `docs/Clase1.pdf`**: `--fuente` (varias,
  separadas por comas, sin distinguir mayúsculas), `--desde AÑO`, `--bibtex` en
  `buscar`, `--n` además de `-n`, y salida en tabla `AÑO CITAS AUTORES TÍTULO`
  ajustada a la terminal (ya no imprime los DOI: van en BibTeX/JSON). Era lo que
  se propuso a @eloyleonorozco en la PR #10; lo hizo el mantenedor.
- **`desde` en las seis fuentes** (D-11): filtros comprobados contra las APIs
  reales. Nuevo `tests/test_desde.py`.
- **`busqueda.py`** (D-12): la búsqueda multifuente que tenía `ui.py` pasa a un
  módulo compartido; la CLI y la UI lo usan. `Articulo.short_authors` nuevo.
  Zotero sin configurar da un error que explica qué variable falta.
- **ruff** (D-13): grupo dev, configuración en `pyproject.toml`, todo el
  proyecto formateado y en verde.
- Probado de verdad: la búsqueda de la demo devuelve los mismos artículos que la
  diapositiva; `--fuente openalex,europepmc --desde 2020 --bibtex` exporta 20.
- Ruido en el diff: el formateo de ruff toca casi todos los ficheros de
  colaboradores. Si alguien tiene una PR abierta contra el `main` anterior, puede
  tener conflictos de formato: que haga `uv run ruff format` tras actualizar.

### 2026-11-17 — Sesión 1: del proyecto vacío a seis fuentes, CLI e interfaz web

Todo el proyecto se construyó en esta sesión (Roberto Bada con Claude Code).

- **Arranque**: proyecto uv con layout `src/` (`30725fa`) y push a
  `Sapere-IA/litmar`.
- **Modelo** (`0083af3`): `Articulo`, `Biblioteca` con BibTeX, clase abstracta
  `Fuente` con reintentos y fuente OpenAlex con test offline. El usuario pidió
  **atributos de clase en inglés** y el resto en español.
- **PRs de colaboradores**, revisadas y comentadas una a una:
  - aceptadas: #3 Crossref (@mattosnh), #6 PANGAEA (@pablo-icm), #4 Europe PMC
    (@aleixop), #7 Zotero (@PurpleFunkyBird), #11 arXiv (@ddietor), #10 CLI y
    persistencia JSON (@eloyleonorozco);
  - cerradas: #8, #9 (arXiv) y #12 (Zotero) por duplicadas, explicando el motivo
    e invitando a aportar sus mejoras (ver «Pendiente de terceros»); #8 además
    tenía un test que fallaba. #2 y #5 las cerró otra persona.
  - #10 tenía conflicto en el README: se fusionaron los dos y se añadió una
    sección por fuente.
- **Seguridad** (`d342dcd`, `621bae5`): `.claude/settings.json` bloquea leer
  `.env` y `.env.*` salvo `.env.example`. Hicieron falta varios intentos por las
  limitaciones de los globs (ver `AGENTS.md` §9).
- **Interfaz web** (`00411b7`, `fae30af`): `src/litmar/ui.py` con Streamlit
  (fuentes, número de resultados, tabla con enlace al DOI, descargas BibTeX y
  CSV), `litmar ui`, `configuracion.py`, `Biblioteca.a_csv()`, `.env.example`,
  carga de `.env` con python-dotenv. Estadísticas de uso de Streamlit
  desactivadas. Probada con búsqueda real en cinco fuentes (25 artículos).
- **Harness de memoria**: `AGENTS.md`, `CLAUDE.md`, `PROGRESS.md`,
  `DECISIONS.md` y hooks `SessionStart`/`Stop`. El usuario eligió: ficheros en el
  repo, el agente anota el progreso solo, y hooks además de instrucciones.
- **Diapositivas**: el usuario añadió `docs/Clase1.pdf` (Clase 1 del curso). De
  ellas salen el contexto del curso y la hoja de ruta de `AGENTS.md` §2, y los
  próximos pasos 1-3 (CLI de la demo, ruff, preparación de la Clase 2).
