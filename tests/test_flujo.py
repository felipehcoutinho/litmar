"""Tests del flujo de revisión con un modelo y unas fuentes falsos: sin clave, sin red."""

from datetime import datetime
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from litmar import cli, configuracion, llm
from litmar.flujo import (
    MAX_REESCRITURAS,
    NO_VERIFICADA,
    Plan,
    citados,
    crear_flujo,
    describir_paso,
    estado_inicial,
    extraer_dois,
    informe_markdown,
    marcar_no_verificadas,
)
from litmar.resumen import ResumenArticulo

PREGUNTA = "¿Cómo afecta el calentamiento a Posidonia oceanica?"


class ModeloFalso:
    """Imita un modelo de chat: planes y resúmenes estructurados, e informes de texto.

    `informes` son las respuestas de sintetizar, en orden; si se acaban, repite la última.
    """

    def __init__(self, informes, consultas=("posidonia warming", "seagrass heat")):
        self.informes = list(informes)
        self.consultas = list(consultas)
        self.sintesis = []  # los mensajes de cada llamada a sintetizar
        self.resumidos = []  # títulos de los artículos resumidos
        self.falla_en = set()  # títulos cuyo resumen lanza una excepción
        self.relevancias = {}

    def with_structured_output(self, esquema, **opciones):
        return _Estructurado(self, esquema)

    def invoke(self, mensajes):
        self.sintesis.append(mensajes)
        texto = self.informes.pop(0) if len(self.informes) > 1 else self.informes[0]
        return AIMessage(content=texto)


class _Estructurado:
    def __init__(self, modelo, esquema):
        self.modelo = modelo
        self.esquema = esquema

    def invoke(self, mensajes):
        if self.esquema is Plan:
            return Plan(queries=self.modelo.consultas)
        texto = mensajes[-1][1]
        titulo = next(linea for linea in texto.splitlines() if linea.startswith("Título: "))
        if titulo in {f"Título: {t}" for t in self.modelo.falla_en}:
            raise RuntimeError("429 Too Many Requests")
        self.modelo.resumidos.append(titulo)
        return ResumenArticulo(
            objective="Objetivo",
            method="Método",
            findings=["Hallazgo"],
            relevance=self.modelo.relevancias.get(titulo, 4),
            limitations="No consta en el resumen.",
        )


class FuenteFalsa:
    def __init__(self, articulos, consultas):
        self.articulos = articulos
        self.consultas = consultas

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def buscar(self, consulta, n, *, desde=None):
        self.consultas.append(consulta)
        return self.articulos[:n]


@pytest.fixture
def articulos(hacer_articulo):
    """Cinco artículos: uno sin resumen (el más citado) y cuatro con distintas citas."""
    return [
        hacer_articulo(doi="10.1/sin", title="Sin resumen", abstract="", citations=999),
        hacer_articulo(doi="10.1/a", title="A", citations=10),
        hacer_articulo(doi="10.1/b", title="B", citations=50),
        hacer_articulo(doi="10.1/c", title="C", citations=30),
        hacer_articulo(doi="10.1/d", title="D", citations=5),
    ]


@pytest.fixture
def consultas_hechas():
    return []


@pytest.fixture
def crear_fuente(articulos, consultas_hechas):
    return lambda nombre: FuenteFalsa(articulos, consultas_hechas)


def ejecutar(modelo, crear_fuente, n=3):
    """Ejecuta el flujo y devuelve (nodos en orden, estado final)."""
    flujo = crear_flujo(modelo, fuentes=["OpenAlex"], n=n, crear_fuente=crear_fuente)
    pasos = []
    estado = None
    for modo, datos in flujo.stream(estado_inicial(PREGUNTA), stream_mode=["updates", "values"]):
        if modo == "values":
            estado = datos
        else:
            pasos += [(nodo, describir_paso(nodo, cambios)) for nodo, cambios in datos.items()]
    return pasos, estado


# --- El grafo coincide con el diagrama


def test_el_grafo_coincide_con_el_diagrama(crear_fuente):
    grafo = crear_flujo(ModeloFalso(["x"]), crear_fuente=crear_fuente).get_graph()

    aristas = {(a.source, a.target) for a in grafo.edges}

    assert aristas == {
        ("__start__", "planificar"),
        ("planificar", "buscar"),
        ("buscar", "resumir_articulos"),
        ("resumir_articulos", "filtrar"),
        ("filtrar", "sintetizar"),
        ("sintetizar", "verificar_citas"),
        ("verificar_citas", "sintetizar"),  # citas inventadas: reescribir
        ("verificar_citas", "__end__"),
    }


# --- Recorrido completo


def test_revision_sin_citas_inventadas(crear_fuente, consultas_hechas):
    modelo = ModeloFalso(["B dice algo [doi:10.1/b] y C lo matiza [doi:10.1/C]."])

    pasos, estado = ejecutar(modelo, crear_fuente)

    assert pasos == [
        ("planificar", "2 consultas"),
        ("buscar", "5 artículos"),
        ("resumir_articulos", "4 resúmenes"),
        ("filtrar", "3 seleccionados"),
        ("sintetizar", "informe (2 citas)"),
        ("verificar_citas", "ok"),
    ]
    assert consultas_hechas == ["posidonia warming", "seagrass heat"]
    # filtrar: resumen y puntuación combinada; el más citado no tiene resumen.
    assert [a.doi for a in estado["selected"]] == ["10.1/b", "10.1/c", "10.1/a"]
    assert estado["cited"] == ["10.1/b", "10.1/c"]
    assert estado["rewrites"] == 0


def test_cita_inventada_vuelve_a_sintetizar(crear_fuente):
    modelo = ModeloFalso(
        [
            "Según [doi:10.1/b] y [doi:10.9999/inventado].",
            "Según [doi:10.1/b].",
        ]
    )

    pasos, estado = ejecutar(modelo, crear_fuente)

    assert pasos[-4:] == [
        ("sintetizar", "informe (2 citas)"),
        ("verificar_citas", "1 cita inválida → reescribir"),
        ("sintetizar", "informe (1 cita)"),
        ("verificar_citas", "ok"),
    ]
    assert estado["rewrites"] == 1
    assert estado["cited"] == ["10.1/b"]
    # Al reescribir, el modelo ve su informe anterior y qué DOI no valían.
    peticion = modelo.sintesis[1][-1][1]
    assert "10.9999/inventado" in peticion


def test_como_mucho_dos_reescrituras_y_luego_se_marcan(crear_fuente):
    modelo = ModeloFalso(["Según [doi:10.1/b] y [doi:10.9999/inventado]."])

    pasos, estado = ejecutar(modelo, crear_fuente)

    assert len(modelo.sintesis) == 1 + MAX_REESCRITURAS
    assert [nodo for nodo, _ in pasos].count("sintetizar") == 1 + MAX_REESCRITURAS
    assert pasos[-1] == (
        "verificar_citas",
        f"1 cita inválida → marcadas como «{NO_VERIFICADA}»",
    )
    assert "10.9999" not in estado["report"]
    assert f"[{NO_VERIFICADA}]" in estado["report"]
    assert estado["unverified"] == ["10.9999/inventado"]
    assert [a.doi for a in citados(estado)] == ["10.1/b"]
    assert any("reescrituras" in aviso for aviso in estado["warnings"])


def test_sin_articulos_no_llama_al_modelo_para_sintetizar():
    modelo = ModeloFalso(["no debería usarse"])

    pasos, estado = ejecutar(modelo, lambda nombre: FuenteFalsa([], []))

    assert modelo.sintesis == []
    assert "No se encontraron artículos" in estado["report"]
    assert pasos[-1] == ("verificar_citas", "ok")


def test_un_resumen_que_falla_no_para_la_revision(crear_fuente):
    modelo = ModeloFalso(["Según [doi:10.1/b]."])
    modelo.falla_en = {"C"}

    _, estado = ejecutar(modelo, crear_fuente)

    assert set(estado["summaries"]) == {"10.1/b", "10.1/a", "10.1/d"}
    assert any("10.1/c" in aviso for aviso in estado["warnings"])


def test_revision_pasa_idioma_a_resumenes_y_a_la_sintesis(monkeypatch, crear_fuente):
    idiomas = []

    def resumir_falso(articulo, pregunta, modelo, *, idioma):
        idiomas.append(idioma)
        return ResumenArticulo(
            objective="Objective",
            method="Method",
            findings=["Finding"],
            relevance=4,
            limitations="None.",
        )

    monkeypatch.setattr("litmar.flujo.resumir", resumir_falso)
    modelo = ModeloFalso(["A report."])
    grafo = crear_flujo(modelo, fuentes=["OpenAlex"], idioma="en", crear_fuente=crear_fuente)

    grafo.invoke(estado_inicial(PREGUNTA))

    assert idiomas and set(idiomas) == {"en"}
    assert "Respond exclusively in English." in modelo.sintesis[0][0][1]


def test_citar_un_seleccionado_sin_resumen_tambien_es_invalido(crear_fuente):
    # El modelo solo ve los seleccionados: citar otro es inventar.
    modelo = ModeloFalso(["Según [doi:10.1/c]."])
    modelo.falla_en = {"C"}

    _, estado = ejecutar(modelo, crear_fuente)

    assert estado["unverified"] == ["10.1/c"]


def test_citar_un_articulo_fuera_del_top_n_es_invalido(crear_fuente):
    modelo = ModeloFalso(["Según [doi:10.1/d]."])

    _, estado = ejecutar(modelo, crear_fuente, n=1)

    assert [a.doi for a in estado["selected"]] == ["10.1/b"]
    assert estado["unverified"] == ["10.1/d"]


def test_planificar_recorta_a_tres_consultas_sin_repetir(crear_fuente, consultas_hechas):
    modelo = ModeloFalso(["x"], consultas=["a", "a", " ", "b", "c", "d"])

    _, estado = ejecutar(modelo, crear_fuente)

    assert estado["queries"] == ["a", "b", "c"]
    assert consultas_hechas == ["a", "b", "c"]


def test_n_tiene_un_maximo(crear_fuente):
    _, estado = ejecutar(ModeloFalso(["x"]), crear_fuente, n=500)

    assert len(estado["selected"]) == 4  # todos los que tienen resumen (máximo: 10)


def test_criterio_combinado_y_aviso_de_citas_no_disponibles(hacer_articulo):
    articulos = [
        hacer_articulo(doi="10.1/viejo", year=2010, citations=100, title="Antiguo"),
        hacer_articulo(doi="10.1/reciente", year=2025, citations=8, title="Reciente"),
        hacer_articulo(doi="10.1/sin-dato", year=2025, citations=None, title="Sin dato"),
    ]
    modelo = ModeloFalso(["x"])
    modelo.relevancias = {
        "Título: Antiguo": 2,
        "Título: Reciente": 4,
        "Título: Sin dato": 5,
    }

    _, estado = ejecutar(
        modelo,
        lambda nombre: FuenteFalsa(articulos, []),
        n=3,
    )

    assert [a.doi for a in estado["selected"]] == [
        "10.1/sin-dato",
        "10.1/reciente",
        "10.1/viejo",
    ]
    assert any(
        "10.1/sin-dato" in aviso and "solo la relevancia" in aviso for aviso in estado["warnings"]
    )


# --- Funciones de apoyo


def test_extraer_dois():
    texto = (
        "Uno [doi:10.1/ABC], otro [DOI: 10.2/x] [doi:10.3/y]. "
        "Repetido [doi:10.1/abc]. Enlace https://doi.org/10.4/z. Sin cita 10.5/w."
    )

    assert extraer_dois(texto) == ["10.1/abc", "10.2/x", "10.3/y", "10.4/z"]


def test_marcar_no_verificadas():
    texto = "Bien [doi:10.1/b]; mal [doi:10.9/X]."

    assert marcar_no_verificadas(texto, ["10.9/x"]) == (
        f"Bien [doi:10.1/b]; mal [{NO_VERIFICADA}]."
    )


def test_informe_markdown_solo_referencia_lo_citado(hacer_articulo):
    b = hacer_articulo(doi="10.1/b", title="Título B")
    c = hacer_articulo(doi="10.1/c", title="Título C")
    estado = {
        "question": PREGUNTA,
        "queries": ["posidonia warming"],
        "selected": [b, c],
        "report": "Según [doi:10.1/b].",
        "cited": ["10.1/b"],
        "warnings": ["OpenAlex respondió con HTTP 503."],
    }

    texto = informe_markdown(estado)

    assert texto.startswith(f"# {PREGUNTA}")
    assert "«posidonia warming»" in texto
    assert "## Referencias" in texto
    assert "Título B" in texto and "https://doi.org/10.1/b" in texto
    assert "Título C" not in texto
    assert "## Avisos" in texto and "HTTP 503" in texto


def test_informe_markdown_localiza_los_titulos(hacer_articulo):
    articulo = hacer_articulo(doi="10.1/b")
    estado = {
        "question": "Research question",
        "queries": ["posidonia"],
        "selected": [articulo],
        "report": "Report.",
        "cited": [articulo.doi],
        "warnings": ["Warning."],
    }

    texto = informe_markdown(estado, "en")

    assert "_Searches: «posidonia»._" in texto
    assert "## References" in texto
    assert "## Warnings" in texto


# --- Comando `litmar revisar`


@pytest.fixture
def sin_red(monkeypatch, crear_fuente):
    """El comando usa el modelo y las fuentes falsos."""
    modelo = ModeloFalso(["Según [doi:10.1/b] y [doi:10.9999/inventado].", "Según [doi:10.1/b]."])
    monkeypatch.setattr(llm, "crear_modelo", lambda: modelo)
    monkeypatch.setattr(configuracion, "crear_fuente", crear_fuente)
    return modelo


def test_cli_revisar_muestra_los_pasos_y_guarda(sin_red, tmp_path, capsys):
    informe = tmp_path / "informe.md"
    bibtex = tmp_path / "citados.bib"

    codigo = cli.main(
        ["revisar", PREGUNTA, "-n", "3", "--informe", str(informe), "--bibtex", str(bibtex)]
    )

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "> planificar         2 consultas" in salida
    assert "> verificar_citas    1 cita inválida → reescribir" in salida
    assert salida.count("> sintetizar") == 2
    assert "Según [doi:10.1/b]." in informe.read_text(encoding="utf-8")
    contenido_bib = bibtex.read_text(encoding="utf-8")
    assert contenido_bib.count("@article") == 1
    assert "10.1/b" in contenido_bib


def test_cli_revisar_sin_modelo_configurado(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("LITMAR_MODELO", raising=False)
    informe = tmp_path / "informe.md"

    codigo = cli.main(["revisar", PREGUNTA, "--informe", str(informe)])

    assert codigo == 1
    assert "LITMAR_MODELO" in capsys.readouterr().err
    assert not informe.exists()


def test_cli_revisar_informe_y_bibtex_distintos(tmp_path, capsys):
    ruta = tmp_path / "mismo"

    assert cli.main(["revisar", PREGUNTA, "--informe", str(ruta), "--bibtex", str(ruta)]) == 1
    assert "distintos" in capsys.readouterr().err


def test_cli_revisar_n_maximo(capsys):
    with pytest.raises(SystemExit):
        cli.main(["revisar", PREGUNTA, "-n", "11"])
    assert "como mucho" in capsys.readouterr().err


def test_el_diagrama_de_docs_esta_al_dia():
    """docs/flujo.md incluye el Mermaid que LangGraph genera del grafo compilado."""
    docs = Path(__file__).parent.parent / "docs" / "flujo.md"
    generado = crear_flujo(None).get_graph().draw_mermaid().strip()

    assert generado in docs.read_text(encoding="utf-8"), (
        "docs/flujo.md no coincide con el grafo: regenera el diagrama (ver el propio fichero)"
    )


# --- Dónde se guardan las revisiones


def test_nombre_carpeta():
    ahora = datetime(2026, 11, 18, 15, 30)

    assert (
        cli.nombre_carpeta("¿Cómo afecta el calentamiento a las praderas de Posidonia?", ahora)
        == "2026-11-18_1530_como-afecta-el-calentamiento-a-las-praderas-de"
    )
    assert cli.nombre_carpeta("¿¿??", ahora) == "2026-11-18_1530_revision"
    assert cli.nombre_carpeta("a" * 80, ahora) == "2026-11-18_1530_" + "a" * 50


def test_carpeta_revision_no_pisa_una_anterior(tmp_path):
    ahora = datetime(2026, 11, 18, 15, 30)
    primera = cli.carpeta_revision("Posidonia", tmp_path, ahora)
    primera.mkdir()

    assert primera.name == "2026-11-18_1530_posidonia"
    assert cli.carpeta_revision("Posidonia", tmp_path, ahora).name == primera.name + "-2"


def test_cli_revisar_guarda_en_su_carpeta_de_ejemplos(sin_red, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert cli.main(["revisar", PREGUNTA, "-n", "3"]) == 0

    (carpeta,) = (tmp_path / "ejemplos" / "revisiones").iterdir()
    assert carpeta.name.endswith("_como-afecta-el-calentamiento-a-posidonia-oceanica")
    assert sorted(f.name for f in carpeta.iterdir()) == ["revision.bib", "revision.md"]
    assert str(carpeta.relative_to(tmp_path) / "revision.md") in capsys.readouterr().out


def test_cli_revisar_que_falla_no_deja_carpeta(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LITMAR_MODELO", raising=False)

    assert cli.main(["revisar", PREGUNTA]) == 1
    assert not (tmp_path / "ejemplos").exists()
