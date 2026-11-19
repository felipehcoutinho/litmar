# PROGRESS — estado y registro de litmar

Memoria viva del proyecto. Cómo se usa y cuándo se actualiza: `AGENTS.md`, §1.
«Estado actual» y «Próximos pasos» se reescriben para que siempre sean ciertos;
el registro solo crece (entradas nuevas arriba).

## Estado actual

_Actualizado: 2026-11-19._

- **`main`**: `67ce3f3`, al día con `origin/main`; los cambios de esta sesión
  están sin commit. Último trabajo: selector multilingüe y revisiones en el
  idioma seleccionado.
  Antes: fusión de la PR #15 (felipehcoutinho), selección combinada por
  relevancia y citas anualizadas (D-23).
- **Curso**: Clase 1 (*Busca*, 17/11/2026) completa respecto a las
  diapositivas. La siguiente es la Clase 2 (*Lee*), el **18/11/2026**; sus
  diapositivas están en `docs/Clase2.pdf` y su plan, abajo. Se está
  construyendo como ensayo, encargo a encargo: hechos los pasos 1 a 6, el 8 y el 9 (`.env.example`, `resumir`, `llm.py`,
  Práctica 1, flujo LangGraph, herramientas, agente, pestaña «Revisión»); la
  votación (7) se hace en clase, probados con un modelo real (Anthropic).
  La Clase 3 (*APIs, reproducibilidad y transferencia*, **19/11/2026**) tiene
  sus diapositivas en `docs/Clase3.pdf` y su plan abajo; hechos los encargos 1
  (API con FastAPI y `litmar servir`) y 2 (web en `/`).
- **Calidad**: 351 tests pasan, sin red, en ~13 s; `ruff check` y
  `ruff format --check` en verde.
- **PRs abiertas**: ninguna.
- **Funciona**:
  - modelo `Articulo` y `Biblioteca` (dedup por DOI, BibTeX, CSV, JSON);
  - seis fuentes: OpenAlex, Crossref, Europe PMC, arXiv, PANGAEA, Zotero; todas
    admiten `desde` (año mínimo);
  - CLI: `litmar buscar "…" --fuente openalex,europepmc --desde 2020 --bibtex
    refs.bib --guardar biblioteca.json`, con salida en tabla; `litmar exportar`;
    `litmar ui`;
  - interfaz web con Streamlit: pestaña «Búsqueda» (varias fuentes, tabla,
    descargas BibTeX/CSV) y pestaña «Revisión» (flujo o agente, pasos en vivo,
    informe con DOI enlazados, descargas);
  - `resumir(articulo, pregunta, modelo)` → `ResumenArticulo` (Pydantic,
    `with_structured_output`), en `src/litmar/resumen.py`;
  - `crear_modelo()` en `src/litmar/llm.py`: modelo de `LITMAR_MODELO` con
    `init_chat_model`, límite de llamadas por minuto y errores claros;
  - `litmar revisar "pregunta"`: flujo LangGraph de seis pasos
    (`src/litmar/flujo.py`) con verificación de citas por código; guarda
    `revision.md` y `revision.bib` (solo lo citado) en
    `ejemplos/revisiones/<fecha_hora_pregunta>/` (ignorado en git);
  - herramientas de LangChain `buscar_articulos` y `listar_fuentes`
    (`src/litmar/herramientas.py`), listas para el agente;
  - `litmar revisar … --modo agente [--aprobar]`: agente de Deep Agents con
    subagente buscador, lista de tareas, límites y citas comprobadas
    (`src/litmar/agente.py`); mismo informe y BibTeX que el flujo;
  - selección por 70 % de relevancia y 30 % de citas/año ajustadas; si falta el
    recuento, se usa solo la relevancia y se avisa. `citations=None` distingue
    el dato ausente de un recuento real de cero;
  - API web con FastAPI (`src/litmar/api.py`, D-24): `litmar servir`,
    `/salud`, `/fuentes`, `/buscar` (varias fuentes, 502 solo si fallan todas)
    y `/revisiones` (flujo o agente; informe y BibTeX, sin guardar en disco);
    documentación en `/docs`; sin token;
  - web en `/` (`src/litmar/web/index.html`, D-25): búsqueda, tabla con DOI
    enlazados, revisión con el informe en Markdown renderizado y descarga del
    BibTeX; selector es/pt-BR/en/ja, informe generado en el idioma seleccionado;
    sin npm, rutas relativas, estética Y2K cromada;
  - configuración por `.env` (plantilla en `.env.example`; todo opcional salvo
    Zotero).

## Próximos pasos

Pendientes, por orden de prioridad sugerido.

0. [ ] **Comprobar el arnés de memoria**. `SessionStart` **funciona**: el
   18/11/2026, al reanudar la sesión, inyectó el estado de este fichero y de git.
   Falta ver en una sesión real que `Stop` pide anotar el progreso cuando hay
   trabajo sin registrar (los casos se probaron a mano con un repo de prueba).
1. [ ] **Clase 3** (19/11/2026): seguir el «Plan de la Clase 3» (abajo);
   encargos 1 y 2 completados. Para probar los encargos 4-6 hace falta Docker
   (no instalado en la máquina del ensayo).
2. [ ] **Clase 2**: seguir el «Plan de la Clase 2» (abajo). El usuario lanza
   los prompts de las diapositivas uno a uno (ensayo). La Clase 2
   está construida; queda la votación (paso 7, en clase). Pendiente: probar con Gemini (solo se ha probado con
   Anthropic). Ojo: con el límite por defecto la primera llamada espera ~6 s (el
   limitador empieza vacío).
3. [ ] **Permisos del JSON**: `Biblioteca.guardar` deja `0600`; aplicar la umask
   con `os.chmod` antes de `os.replace`. Propuesto en la PR #10.
4. [ ] **Mover el helper `cliente` de `tests/test_fuentes.py` a `conftest.py`**,
   para que `test_pangaea.py` no importe de otro fichero de tests.
5. [ ] **`pyproject.toml`**: cambiar `description = "Add your description here"`.
6. [ ] **«Desde el año» en la UI**: `buscar_en_fuentes` ya admite `desde`; falta
   el campo en `ui.py`.
7. [ ] **Ideas para la UI** (sin pedir aún): guardar/cargar la biblioteca JSON,
   filtrar u ordenar resultados, mostrar de qué fuente viene cada artículo.

## Plan de la Clase 2 (de `docs/Clase2.pdf`)

Los encargos que se lanzan «en directo», en orden. Cada uno trae en la
diapositiva una columna «En qué fijarse»: el resultado debe superarla. Consultar
la documentación actual de LangChain, LangGraph y deepagents antes de programar
(cambian rápido) y proponer plan antes de código.

1. [x] **`.env`** (diapositiva 4; en `.env.example` el 18/11): `LITMAR_MODELO=google_genai:gemini-3.8-flash`
   + `GOOGLE_API_KEY`, o `anthropic:claude-sonnet-5-5` + `ANTHROPIC_API_KEY`. El
   plan gratuito de Gemini tiene límites por minuto (429) y Google puede usar lo
   enviado: solo datos públicos.
2. [x] **Resumen estructurado** (18/11, `resumen.py`; probar con modelo real): `resumir(articulo, pregunta, modelo)` → objeto
   Pydantic `ResumenArticulo` (objetivo, método, hallazgos, relevancia 1-5
   respecto a la pregunta, limitaciones) con `with_structured_output`. Cada
   campo con descripción (el modelo la lee). Sin resumen → no llamar al modelo.
   Test con modelo falso, sin clave ni red.
3. [x] **Modelo intercambiable** (18/11, `llm.py`): `src/litmar/llm.py` con `crear_modelo()` que lee
   `LITMAR_MODELO` y usa `init_chat_model`; límite de llamadas por minuto para el
   plan gratuito; si falta la clave, error claro que diga qué poner en el `.env`.
   Ningún nombre de modelo ni clave en el código; cambiar de modelo = cambiar el
   `.env`.
4. [x] **Práctica 1** (18/11) de los alumnos: `ejemplos/resumir.py` (busca 3 artículos y
   los resume). Puede convenir tenerlo hecho como referencia.
5. [x] **Flujo LangGraph** (18/11; D-17, D-18) (`src/litmar/flujo.py`): estado `TypedDict`
   (`EstadoRevision`: pregunta, artículos, resúmenes, informe…); nodos
   `planificar` (LLM: pregunta → 2-3 búsquedas), `buscar` y `filtrar` (código:
   fuentes y Biblioteca; sin duplicados, los N con mejor puntuación),
   `resumir_articulos` (con `resumir()` para los candidatos con resumen),
   `sintetizar` (LLM, cita por DOI) y
   `verificar_citas` (código: cada DOI citado está entre los seleccionados; si
   no, vuelve a `sintetizar`, máximo 2 veces). Comando `litmar revisar
   "pregunta" --modo flujo` que muestra cada paso (ver demo, diapositiva 21) y
   guarda el informe y el BibTeX de lo citado. Primero plan y diagrama Mermaid.
6. [x] **Herramientas** (18/11, D-20) (`src/litmar/herramientas.py`): `buscar_articulos(consulta,
   fuente, n)` (reutiliza `crear_fuente`) y `listar_fuentes` (usa
   `fuentes_disponibles`), con `@tool` de LangChain. Máximo 10 en el código;
   errores como mensaje; devuelven título, año, DOI, citas y resumen recortado;
   docstrings pensados para el modelo; avisar de que PANGAEA da datos, no
   artículos. Tests sin red.
7. [ ] **Votación en clase** (una de tres): Zotero por MCP
   (`github.com/Sapere-IA/zotero-mcp`, solo herramientas de lectura, arranque en
   el `.env`; el MCP solo para PDFs y notas, sin duplicar la búsqueda), Semantic
   Scholar como herramienta de citas, o una fuente de CSV/BD local del grupo.
8. [x] **Agente con Deep Agents** (18/11, D-21): `litmar revisar … --modo agente` con
   `create_deep_agent` y `herramientas.py`; instrucciones: planificar con lista
   de tareas, buscar en varias fuentes, citar solo DOIs que den las herramientas
   y decir lo que no encontró. Mismo formato de informe y BibTeX que el flujo.
   Subagente buscador. `--aprobar` con `interrupt_on` para pedir permiso antes de
   buscar. Límite de pasos (si se alcanza, escribir hasta dónde llegó) con test de
   modelo falso.
9. [x] **Pestaña «Revisión» en la UI** (18/11, D-22): pregunta, modo flujo/agente, fuentes y
   número de artículos; pasos en vivo; informe con los DOI como enlaces; mensaje
   claro si falta la clave. Reutilizar las funciones de revisión (refactor
   mínimo si imprimen por pantalla) sin romper la terminal.
10. [ ] **Para la Clase 3**: los alumnos deben comprobar `docker run hello-world`
    (la Práctica 2 de la Clase 3 lo necesita; sin Docker, en parejas).

## Plan de la Clase 3 (de `docs/Clase3.pdf`)

*APIs, reproducibilidad y transferencia*, 19/11/2026. Mismo método que la
Clase 2: encargos «en directo» copiados de las diapositivas, cada uno con su
columna «En qué fijarse», y **plan antes que código** (las diapositivas lo
piden explícitamente: «Primero propón el contrato», «Antes, dime qué rutas
usará»). Consultar la documentación actual de FastAPI, uvicorn, uv (guía de
Docker) y nginx antes de escribir código.

Guion de la clase: repaso (d. 3) → **01 Tu propia API** (d. 4-14: vocabulario
HTTP, FastAPI, encargos 1 y 2, Práctica 1) → descanso → **02 Docker** (d. 16-28:
imagen/contenedor/capas, Dockerfile, ciclo de vida, secretos, compose,
encargos 3 y 4, Práctica 2, checklist de reproducibilidad) → **03 Cierre**
(d. 29-34: recapitulación, lluvia de ideas, «del caso de uso al primer
encargo», cómo seguir).

1. [x] **API con FastAPI** (diapositiva 9; hecho el 19/11, D-24) en `src/litmar/api.py`.
   Prompt: «Expón litmar como API con FastAPI en src/litmar/api.py: GET /salud,
   GET /fuentes, GET /buscar (varias fuentes y año mínimo, con
   buscar_en_fuentes) y POST /revisiones (flujo o agente, con flujo.revisar y
   agente.revisar; devuelve el informe y el BibTeX, no los guarda en disco).
   Primero propón el contrato: parámetros, modelos de entrada y salida y códigos
   de error de cada ruta. Token opcional desde el .env. Tests con TestClient,
   sin red, y un comando litmar servir.»
   - En qué fijarse: (1) ¿el contrato tiene sentido antes de programar?
     (2) ¿llama a `buscar_en_fuentes` y a `revisar` o duplica lógica? (3) `n=0`
     en `/docs` da 422; (4) ¿qué devuelve si falla una fuente o falta la clave
     del LLM?
   - Lo que hay que decidir al proponer el contrato (anotar en `DECISIONS.md`):
     - **Errores** (d. 6 y 11: 200, 422, 401, 502): `buscar_en_fuentes` ya
       recoge los errores por fuente; propuesta: 200 con una lista `errores` si
       alguna fuente responde, **502** solo si fallan todas. Falta de
       configuración del modelo (`ErrorDeConfiguracion`): **503** con el mensaje
       de qué poner en el `.env`, sin claves ni peticiones (§7).
     - **Token**: `LITMAR_API_TOKEN` (nombre a confirmar) en `.env.example`;
       sin él la API es abierta; con él, `Authorization: Bearer …` comparado con
       `secrets.compare_digest`, 401 si no cuadra. ¿`/salud` y `/` sin token?
       Si hay token, la web (encargo 2) necesita pedirlo o la API no la deja
       buscar: decidir antes de ese encargo.
     - **`/revisiones` es síncrona** y tarda minutos (d. 11 «Tareas largas»: en
       producción se devolvería un id; aquí no, a propósito). `--aprobar` no
       tiene sentido en HTTP: el modo agente va sin aprobación.
     - **Límites**: `n` entre 1 y 50 (`Query(ge=1, le=50)`, d. 8) en `/buscar`;
       en `/revisiones`, el `MAX_SELECCIONADOS` del flujo. «Límites de uso» por
       cliente (d. 11) solo se menciona.
     - **Modelos de salida Pydantic** (`ArticuloSalida.desde(articulo)`, d. 8):
       mismos campos que el JSON de `Biblioteca`.
   - `litmar servir [--host 127.0.0.1] [--puerto 8000] [--recargar]` con
     uvicorn (con `--recargar` hay que pasar la app como texto,
     `"litmar.api:app"`). `uv add fastapi uvicorn` (TestClient usa httpx, que ya
     está). Sección en el README.
   - Demo (d. 10): `uv run litmar servir --recargar`, `/docs`, `curl
     "http://127.0.0.1:8000/buscar?consulta=posidonia&n=2"`.
2. [x] **Web en HTML y JavaScript** (diapositiva 13; hecho el 19/11, D-25; falta
   probarla en un navegador) en
   `src/litmar/web/index.html`. Prompt: «Crea una página web en
   src/litmar/web/index.html (HTML, CSS y JavaScript, sin npm ni compilación)
   que use nuestra API: búsqueda con fuentes y año mínimo, tabla con los DOI
   enlazados y un botón Revisar que llame a POST /revisiones, muestre el
   informe y deje descargar el BibTeX. Que la API la sirva en /. Avisa de que
   una revisión tarda minutos y muestra los errores con claridad. Usa rutas
   relativas (/buscar), sin la dirección del servidor. Antes, dime qué rutas
   usará y con qué parámetros.»
   - En qué fijarse: (1) solo rutas del contrato, sin cambiar la API; (2) F12 >
     Red: qué pide y qué devuelve; (3) por qué no hace falta CORS (mismo origen)
     y qué pasaría en otro dominio; (4) qué ve el usuario mientras espera o si
     algo falla.
   - Comprobar que `uv_build` mete `web/index.html` en el paquete (la API la
     lee del paquete, no de la carpeta del repo) y test de que `/` devuelve la
     página. El informe llega en Markdown: decidir si se muestra como texto o
     con una conversión mínima sin librerías externas (sin npm).
3. [ ] **Práctica 1** de los alumnos (d. 14, 20 min): `litmar servir`, web en
   `/` y `/docs`, F12 > Red, provocar un 422, pedir a la IA una mejora o una
   ruta nueva (exportar en BibTeX) con su test. Puede convenir tener hecha la
   ruta de BibTeX como referencia (sin integrarla).
4. [ ] **Dockerfile** (diapositivas 19-20). Prompt: «Crea un Dockerfile para
   litmar usando uv con la imagen oficial de Astral y Python 3.12 slim. Instala
   las dependencias desde uv.lock antes de copiar el código para aprovechar la
   caché, sin dependencias de desarrollo (pytest, ruff y Streamlit no hacen
   falta en el servidor), usuario no root, y nada de secretos dentro: añade un
   .dockerignore. Comenta cada línea.» Y la revisión: «Revisa este Dockerfile
   como un experto en seguridad y reproducibilidad. ¿Qué se copia que no
   debería? ¿Qué capa se rompe en cada cambio? No cambies nada.»
   - Referencia: el Dockerfile de la d. 19 (`FROM python:3.12-slim`, `COPY
     --from=ghcr.io/astral-sh/uv`, `UV_NO_DEV=1`, `uv sync --locked
     --no-install-project`, `COPY . .`, `uv sync --locked`, `useradd`, `USER
     app`, `EXPOSE 8000`, `CMD … litmar servir --host 0.0.0.0`).
   - Ojo: Streamlit está en el extra `ui` y en el grupo `dev`, así que no entra
     en la imagen; `litmar ui` dentro del contenedor debe dar un error claro
     (ya importa Streamlit solo al usarlo). El `.dockerignore` debe excluir
     `.env`, `.env.*` (salvo `.env.example`), `.venv` (binarios de macOS),
     `.git`, cachés, `tests/`, `docs/` (PDFs) y `ejemplos/revisiones/`, pero
     **no** `README.md` (`pyproject` lo declara y `uv_build` lo necesita).
     Comprobar que `uv run` como usuario `app` no intenta reescribir `.venv`
     (propiedad de root); si lo hace, `--no-sync` o `chown`.
5. [ ] **compose.yaml con dos servicios** (diapositiva 24). Prompt: «Crea un
   compose.yaml con dos servicios: api (nuestra imagen, litmar servir en
   0.0.0.0, puerto 8000, .env al arrancar) y web (imagen oficial de nginx,
   puerto 8080) que sirva src/litmar/web y reenvíe a api las rutas de la API
   usando el nombre del servicio, con tiempo de espera de varios minutos para
   las revisiones. Explícame cada línea y cómo arrancar, ver los logs y parar.»
   - En qué fijarse: (1) cómo encuentra `web` a `api` (DNS de compose por
     nombre de servicio); (2) qué rutas reenvía nginx y si funciona `/docs`
     (necesita también `/openapi.json`); (3) el `.env` llega solo a `api` y no
     está en ninguna imagen; (4) si se para `api`, qué muestra la web (502 de
     nginx: la web debe mostrarlo claro, enlaza con el encargo 2).
   - nginx con `proxy_read_timeout` (y `proxy_send_timeout`) de varios minutos;
     su configuración en un fichero del repo montado de solo lectura. Demo
     (d. 25): `docker compose up --build`, `docker compose ps`,
     `localhost:8080` (web) y `localhost:8000/docs` (API). Variante de
     desarrollo comentada (d. 23): `volumes: [./src:/app/src]` y `--recargar`.
6. [ ] **Práctica 2** (d. 27, 30 min; sin Docker, en parejas): `docker compose
   up --build` (o `podman compose`), una búsqueda y una revisión en `:8080`,
   comprobar que el `.env` no está en la imagen (p. ej. `docker run --rm litmar
   ls -la /app`), cambiar código y ver qué capas se rehacen.
7. [ ] **Checklist de reproducibilidad** (d. 28): `uv.lock`, `.env.example`
   documentado, ningún secreto en git ni en la imagen, tests sin internet,
   README con cómo instalar y ejecutar (añadir API y Docker), funciona en una
   máquina limpia. Aprovechar para cerrar el paso 5 de «Próximos pasos»
   (`description` de `pyproject.toml`).
8. [ ] **Cierre** (d. 29-34): sin código. Lluvia de ideas (datos, literatura,
   servicios), prompt «del caso de uso al primer encargo» (d. 32). La d. 33
   avisa de que la clave del curso caduca el 19/11 a las 14:00 y recomienda
   Gemini con plan gratuito.

Requisitos en la máquina del ensayo: **Docker no está instalado** (comprobado
el 18/11, tampoco Podman). Sin él se pueden escribir el Dockerfile y el
compose, pero no probarlos (encargos 4-6).

## Cabos sueltos

- **Subagente `general-purpose` del agente**: Deep Agents lo ofrece siempre en
  `task`, con las herramientas del principal (no puede buscar). Si en clase
  molesta, se quita con `register_harness_profile(<clave del modelo>,
  HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)))`.
- **El buscador ve resúmenes recortados a 400 caracteres** (`LARGO_RESUMEN` en
  `herramientas.py`): en la prueba real el informe del agente dice varias veces
  que «los resúmenes recibidos no permiten…». Buen ejemplo para el taller
  (flujo contra agente: el flujo resume el resumen completo).
- **Europe PMC deja HTML en títulos y resúmenes** (`<i>…</i>`, `&lt;i&gt;`),
  visto el 18/11 al probar `buscar_articulos`. Afecta a la tabla de la CLI, al
  BibTeX y a lo que ve el modelo. Limpiarlo en `fuentes/europepmc.py` (con
  `html.unescape` y quitar etiquetas) y añadir un test con un título así.
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

### 2026-11-19 — Selector de idioma e informes multilingües

- `src/litmar/web/index.html`: selector para español, portugués de Brasil,
  inglés y japonés; traduce los rótulos de la interfaz y envía `language` en
  `POST /revisiones`.
- `src/litmar/api.py`, `flujo.py`, `agente.py` y `resumen.py`: el idioma se
  valida y propaga por el flujo completo; los prompts de resumen, síntesis o
  agente lo reciben, y los encabezados/fallbacks generados por el código se
  localizan. Español sigue siendo el predeterminado. D-26.
- README y `AGENTS.md` actualizados. Pruebas focalizadas y suite completa:
  351 tests; Ruff y formato en verde. Validación con navegador de los cuatro
  idiomas y del `language: "ja"` enviado por la web con una respuesta simulada;
  no se hizo una llamada real a un modelo.

### 2026-11-19 — Iconos en los apartados de la web

- Añadidos 🔎 y ✨ a los títulos de Búsqueda y Revisión. Se marcan como
  decorativos para que no añadan ruido a lectores de pantalla.

### 2026-11-19 — Estética Y2K para la web de la API

- Rediseñada la capa visual de `src/litmar/web/index.html` con reflejos
  cromados, gradientes violeta/cian, paneles translúcidos y controles brillantes.
  Se mantuvieron intactos el contrato y el comportamiento de búsqueda/revisión.
- Comprobación visual en navegador y validación: 343 tests, Ruff y formato en
  verde.

### 2026-11-19 — Sesión 3: web en HTML y JavaScript (Clase 3, encargo 2)

- Antes del código, las rutas que usaría: `/fuentes` (casillas), `/buscar`
  (`URLSearchParams`, `fuente` repetido) y `/revisiones` (JSON). El usuario
  eligió un campo propio para la pregunta y el informe con el Markdown
  renderizado (D-25).
- `src/litmar/web/index.html` (un fichero, ~500 líneas) y `GET /` en `api.py`,
  fuera del esquema. Aviso fijo de que la revisión tarda minutos; mientras,
  botón desactivado y un reloj. Errores en rojo según el código (422 campo a
  campo, 502/503 con el `detail`, sin conexión, respuesta sin JSON).
- Comprobado: 343 tests (dos nuevos: `/` devuelve la página; solo usa rutas
  del contrato y ninguna dirección absoluta); `uv build` mete
  `litmar/web/index.html` en el wheel; el conversor de Markdown, con Node,
  sobre el informe real del 19/11 y casos difíciles (tablas, sublistas,
  `snake_case`, `<script>` escapado, `javascript:` sin enlazar).
- **Sin probar en un navegador**: Claude in Chrome no estaba disponible en la
  sesión. Pendiente: abrir `litmar servir` → `/`, buscar, revisar y mirar F12 >
  Red.

### 2026-11-19 — Sesión 3: API con FastAPI (Clase 3, encargo 1)

- Primero el contrato, como pide la diapositiva 9. El usuario eligió: `/buscar`
  devuelve un objeto con `errors` (no una lista como la demo de la d. 10),
  **sin token** y campos JSON en inglés. Detalle y códigos de error en D-24.
- `src/litmar/api.py` solo traduce HTTP a las funciones que ya había
  (`buscar_en_fuentes`, `flujo.revisar`, `agente.revisar`, `crear_modelo`);
  `litmar servir [--host] [--puerto] [--recargar]` en `cli.py`. `uv add
  fastapi uvicorn` (fastapi 0.165, uvicorn 0.54) como dependencias principales.
- Los tests destaparon una trampa: FastAPI no pasa el valor por defecto por el
  `AfterValidator` (llegaba «openalex» a `crear_fuente`); arreglado con
  `validate_default=True` y anotado en AGENTS.md §9.
- `tests/test_api.py` (29 tests): 422 (`n=0`, fuente desconocida, Zotero sin
  configurar, pregunta vacía…), 502 si fallan todas las fuentes o el modelo
  (sin claves en el mensaje), 503 sin `LITMAR_MODELO`, nada escrito en disco y
  `litmar servir` con uvicorn falso.
- Prueba real con `litmar servir`: `/buscar` en OpenAlex y Europe PMC (4
  artículos), `n=0` → 422, `/docs` carga; `/revisiones` en modo flujo con
  `n=2` tardó 194 s y devolvió un informe con 2 citas comprobadas y su BibTeX.
  Los pasos salen en el log de uvicorn. Ojo: resumió 23 artículos para elegir
  2 (comportamiento de la PR #15; falta comentarlo en la PR).
- README: sección «API web».

### 2026-11-19 — Sesión 3: fusión de la PR #15 y repaso de la memoria

- El usuario fusionó la PR #15 (`45de0c3`) resolviendo conflictos en
  `PROGRESS.md` y `AGENTS.md` a mano. El código quedó bien (312 tests, ruff en
  verde), pero `PROGRESS.md` no: la línea de Calidad del alumno partía el punto
  «Curso», había dos líneas de Calidad, el commit de `main` era `db90288` y el
  registro llevaba notas locales del alumno (rama sin enviar, `stash@{0}`). Se
  arregló «Estado actual», se quitó la entrada del `stash` y se rehízo la de la
  PR. Lección: al integrar PRs de alumnos, sus cambios en `PROGRESS.md`
  describen su máquina; hay que reescribirlos para el repositorio (§11).

### 2026-11-18 — Selección por relevancia y citas anualizadas

- D-23 sustituye el orden por citas totales (D-17): se combina 70 % de
  relevancia (1–5) con 30 % de la puntuación de citas anualizadas, ajustada a
  escala 1–5. Sin recuento disponible, se usa solo relevancia.
- `Articulo.citations` ahora permite `None`; arXiv, Zotero y PANGAEA lo usan al
  no ofrecer recuento. OpenAlex, Crossref y Europe PMC preservan el cero y
  distinguen un campo ausente. UI, CLI, herramientas e informes identifican el
  dato ausente.
- El flujo resume todos los candidatos con resumen antes de escoger los N, por
  lo que puede hacer más llamadas al modelo. En modo agente, las herramientas
  exponen la tasa/ajuste y el prompt pide la misma puntuación.
- Escrito por felipehcoutinho en su fork (rama `feat/citation-aware-selection`,
  `c3a87c9`) y enviado como PR #15.
- Validación: 312 tests, Ruff, formato y lockfile en verde.

### 2026-11-18 — Sesión 2: diapositivas de la Clase 3

- Añadido `docs/Clase3.pdf` (*APIs, reproducibilidad y transferencia*,
  19/11/2026, 35 diapositivas); commit `9dbd220`. Hoja de ruta de `AGENTS.md`
  actualizada.
- Leídas enteras y volcadas en «Plan de la Clase 3»: cuatro encargos en
  directo (API FastAPI en `api.py` + `litmar servir`, web en
  `src/litmar/web/index.html`, Dockerfile con uv, `compose.yaml` con api +
  nginx), dos prácticas, la checklist de reproducibilidad y el cierre. Para
  cada encargo se anotaron el prompt literal, «En qué fijarse» y las decisiones
  que habrá que tomar al proponer el contrato (códigos 502/503, token, revisión
  síncrona, sin `--aprobar` en HTTP). Principios de la Clase 3 añadidos a
  `AGENTS.md` §2. Docker no está instalado en esta máquina: avisado en el plan.

### 2026-11-18 — Sesión 2: pestaña «Revisión» en la UI (Clase 2, encargo 9)

- Prompt literal de la diapositiva 40. Refactor mínimo (D-22): `flujo.revisar()`
  y `agente.revisar()` con `mostrar`; la CLI las usa y su salida no cambia.
- `ui.py`: `app()` con pestañas; `busqueda()` (lo de antes) y `revision()`:
  pregunta, modo, fuentes, número de artículos; pasos en vivo con `st.status`;
  informe con `flujo.enlazar_dois` (DOI → enlaces) y descargas; aviso del
  `.env` y botón desactivado sin modelo. Sin `--aprobar` en la UI.
- Tests: 6 nuevos en `tests/test_ui.py` (sin modelo, flujo completo con modelo
  falso, pregunta vacía, agente con `agente.revisar` sustituido, límite,
  `enlazar_dois`). 299 tests.
- Prueba real: la pestaña con `AppTest` y el modelo del `.env` (flujo, Europe
  PMC, 3 artículos): 6 pasos, 3 citas enlazadas, 46 s. `litmar ui --server.headless
  true` arranca (health ok). No se ha visto en un navegador.

### 2026-11-18 — Sesión 2: arreglo de `--aprobar` con buscadores en paralelo

- El usuario probó `--modo agente --aprobar` y falló tras aprobar dos
  búsquedas: «When there are multiple pending interrupts, you must specify the
  interrupt id when resuming». El agente lanzó dos buscadores a la vez, cada uno
  con su pausa; el código solo guardaba la última y reanudaba sin id.
- Arreglo: `agente.ejecutar()` recoge todas las interrupciones del principal
  por `id`, pide una decisión por cada búsqueda y reanuda con
  `Command(resume={id: {"decisions": [...]}})`. El bucle, que estaba duplicado
  en la CLI y en los tests (por eso los tests no lo vieron), vive ahora solo
  ahí. Trampa en `AGENTS.md` §9.
- 2 tests de regresión (dos encargos en paralelo, aprobar uno y rechazar otro, y
  la CLI); se comprobó que fallan con el código anterior con el mismo error.
  293 tests.

### 2026-11-18 — Sesión 2: agente con Deep Agents (Clase 2, encargo 8)

- Prompt literal de la diapositiva 36. Antes, documentación actual: subagente
  `web-fetch` sobre docs.langchain.com (HITL, subagentes, backends, perfiles,
  streaming) y comprobación en el código instalado (deepagents 0.7.39) de lo
  que no aclaraban. Hallazgos en `AGENTS.md` §9.
- `src/litmar/agente.py` (D-21): `crear_agente`, `Registro`, `Narrador`,
  `interrupcion`, `estado_final`. `herramientas.py` se partió en `buscar()` y
  `describir_fuentes()` (con `permitidas` y `desde`) para reutilizarlas.
- CLI: `--modo agente`, `--aprobar` (pregunta S/n/e en la terminal), `-n` como
  máximo de artículos del agente; `_revisar` dividido en `_con_flujo` y
  `_con_agente`.
- `tests/test_agente.py` (18 tests): modelo de guion, herramientas de cada
  agente, recorrido completo, DOI inventado, límite de pasos y de búsquedas,
  fuentes permitidas, aprobar/rechazar/editar, CLI. 291 tests.
- Prueba real (Anthropic, pregunta de la demo): plan de 4 tareas, 3 encargos al
  buscador en paralelo, 9 búsquedas, 6 citas verificadas, «Lo que no se
  encontró» bien hecho; 1:52 min. `--aprobar` no se probó con el modelo real
  (necesita terminal interactiva); sí con tests.

### 2026-11-18 — Sesión 2: herramientas (Clase 2, encargo 6)

- Prompt literal de la diapositiva 28. `src/litmar/herramientas.py`:
  `buscar_articulos(consulta, fuente="OpenAlex", n=5)` y `listar_fuentes()` con
  `@tool(parse_docstring=True)`; `HERRAMIENTAS` para el agente. D-20.
- «En qué fijarse»: (1) una herramienta para todas las fuentes, con `fuente`
  como parámetro; (2) los docstrings dicen qué devuelve, cuándo usarla, que solo
  se citen sus DOI y que PANGAEA da datos; (3) `n = max(1, min(n, 10))` en el
  código; (4) si una fuente falla, el modelo recibe «Error: OpenAlex respondió
  con HTTP 503. Prueba con otra fuente.», sin la URL.
- Refactor: `busqueda.mensaje_de_error()` (lo usan `buscar_en_fuentes` y la
  herramienta), con un caso para errores inesperados (solo el tipo).
- `tests/test_herramientas.py` (23 tests, sin red). 273 tests.
- Prueba real: las dos herramientas contra las APIs (Europe PMC, PANGAEA, una
  fuente inexistente) y `bind_tools` con Claude: pidió
  `buscar_articulos(consulta="ocean acidification coral", n=3)`. Se vio HTML en
  los títulos de Europe PMC (anotado en «Cabos sueltos»).

### 2026-11-18 — Sesión 2: salidas de `litmar revisar` en `ejemplos/revisiones/`

- Petición del usuario: guardar las salidas en `ejemplos/`, cada una en su
  subdirectorio. Decidió (herramienta de preguntas) nombre con fecha, hora y
  pregunta, y no versionarlas (D-19).
- `cli.py`: `nombre_carpeta()` y `carpeta_revision()`; `--informe` y `--bibtex`
  ya no tienen valor por defecto (si faltan, van a la carpeta de la ejecución).
  `.gitignore`: `ejemplos/revisiones/`. 4 tests nuevos (nombre, no pisar, CLI
  sin rutas, una revisión que falla no deja carpeta). 250 tests.

### 2026-11-18 — Sesión 2: flujo LangGraph y `litmar revisar` (Clase 2, encargo 5)

- Prompt literal de la diapositiva 19. Primero plan y diagrama Mermaid; el
  usuario pidió alinearlo con la diapositiva 18 (cambio: `planificar` da 2-3
  búsquedas, no 1-3) y decidió, con la herramienta de preguntas: «mejores» = más
  citados (D-17), marcar las citas inválidas tras 2 reescrituras (D-18), estado
  en inglés (D-2), y commit previo de la Práctica 1 (3416434, ya en `origin`).
- `src/litmar/flujo.py`: `EstadoRevision` (TypedDict; `warnings` con reductor
  `operator.add`), seis nodos como clausuras dentro de `crear_flujo(modelo,
  fuentes, n, desde, crear_fuente)`, arista condicional `decidir`. Límites en
  código: 3 consultas, 10 seleccionados, 2 reescrituras. `planificar` y
  `resumir` usan `method="json_schema"`. `sintetizar` sin resúmenes no llama al
  modelo; al reescribir le pasa su informe y los DOI inválidos. Las citas se
  extraen con una regex (`[doi:…]` o `doi.org/…`) y se normalizan con
  `normalizar_doi`. `describir_paso` da las líneas de la demo (no imprime: la
  UI la reutilizará). Las referencias del informe las genera el código.
- CLI: `litmar revisar "pregunta" [--modo flujo] [--fuente] [-n ≤10] [--desde]
  [--informe revision.md] [--bibtex revision.bib]`, con `stream(stream_mode=
  ["updates", "values"])`. Errores del modelo → mensaje y código 1.
- Dependencia nueva: `langgraph` (1.2.22). `tests/test_flujo.py` (16 tests):
  aristas del grafo = diagrama, recorrido completo, reescritura, máximo de 2,
  sin artículos, resumen que falla, CLI. 245 tests.
- Prueba real (Anthropic) con la pregunta de la demo: 3 consultas, 50
  artículos, 6 seleccionados, informe con 5 citas, todas verificadas, 1:35 min.
  El filtro por citas metió dos trabajos generales sobre olas de calor: buen
  ejemplo para la Práctica 2. No se vio una reescritura real (el modelo no
  inventó); el camino está cubierto por tests.
- A petición del usuario, `docs/flujo.md`: el diagrama Mermaid didáctico (LLM /
  CÓDIGO, como la diapositiva 18), una tabla de qué lee y escribe cada nodo en
  el estado, y el Mermaid que genera LangGraph (`get_graph().draw_mermaid()`).
  Un test falla si este último deja de coincidir con el grafo. 246 tests.

### 2026-11-18 — Sesión 2: Práctica 1 (`ejemplos/resumir.py`) y prueba real

- `ejemplos/resumir.py`: carga `.env`, crea el modelo (si falta algo, imprime el
  error y sale con 1), busca en OpenAlex los 3 primeros artículos sobre «ocean
  acidification» que tienen resumen (pide 12) y muestra el resumen de cada uno
  con su enlace al DOI. Si un resumen falla (p. ej. 429), sigue con los demás.
  `TEMA` y `PREGUNTA` arriba para que cada alumno ponga los suyos. Test en
  `tests/test_ejemplos.py` con fuente y modelo falsos.
- **Primera prueba real** (el usuario ya tiene `anthropic:claude-sonnet-5-5` en
  el `.env`): los tres resúmenes salen bien y marcan lo que no está en el
  resumen («No consta…»). `langchain-anthropic` avisaba de que el método por
  defecto (`function_calling`) puede fallar en ese modelo: `resumir` pasa ahora
  `method="json_schema"`, válido también en Gemini. Trampa anotada en
  `AGENTS.md` §9.
- 229 tests.

### 2026-11-18 — Sesión 2: `llm.py` (Clase 2, encargo 3)

- Prompt literal de la diapositiva 12. `src/litmar/llm.py`: `crear_modelo()` lee
  `LITMAR_MODELO` (formato `proveedor:modelo`), comprueba la clave del proveedor
  (`GOOGLE_API_KEY`/`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) y
  llama a `init_chat_model` con un `InMemoryRateLimiter`. Si falta algo,
  `ErrorDeConfiguracion` con la línea exacta que hay que añadir al `.env`.
- Límite: 10 llamadas/min por defecto, `LITMAR_LLAMADAS_POR_MINUTO` (0 = sin
  límite). Decisiones D-15 (dependencias) y D-16 (límite, `.env` no se carga en
  `llm.py`).
- Dependencias nuevas: `langchain`, `langchain-google-genai`,
  `langchain-anthropic` («En qué fijarse» 3).
- `.env.example`: sección del modelo de lenguaje. README: tabla de variables y
  ejemplo con `crear_modelo`.
- `tests/test_llm.py` (16 tests): crean el objeto del modelo con claves falsas,
  sin llamarlo. 227 tests.
- Prueba real: no se pudo, el `.env` no tiene `LITMAR_MODELO` (se vio el
  mensaje de error, que es el punto 2 de la diapositiva).

### 2026-11-18 — Sesión 2: `resumir` (Clase 2, encargo 2)

- Prompt literal de la diapositiva 11. Nuevo `src/litmar/resumen.py`:
  `ResumenArticulo` (Pydantic) con `objective`, `method`, `findings` (lista),
  `relevance` (1-5, validado con `ge`/`le`) y `limitations`, todos con
  descripción porque el modelo las lee. `resumir()` devuelve `None` sin llamar
  al modelo si no hay resumen, y las instrucciones piden usar solo título y
  resumen y escribir «No consta en el resumen.» en vez de inventar.
- Campos en inglés aunque la diapositiva los nombra en español: convención D-2.
- El modelo se recibe como parámetro (lo creará `llm.py`); `resumen.py` no lee
  claves ni conoce proveedores. Dependencias nuevas: `pydantic` y
  `langchain-core` (de ahí viene `with_structured_output`).
- `tests/test_resumen.py`: modelo falso propio (solo `with_structured_output` e
  `invoke`), sin clave ni red. 211 tests. Sección en el README.
- Sin probar con un modelo real: falta `llm.py` (siguiente encargo).

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
