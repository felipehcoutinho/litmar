"""Tests de la API con TestClient: sin red, sin servidor y sin clave del modelo."""

import httpx
import pytest
from fastapi.testclient import TestClient

from litmar import cli
from litmar.api import app
from litmar.fuentes import Fuente

cliente = TestClient(app)


class FuenteFalsa(Fuente):
    def __init__(self, articulos=(), error=None):
        super().__init__()
        self.articulos = list(articulos)
        self.error = error
        self.pedidos = []

    def buscar(self, consulta, n=10, *, desde=None):
        self.pedidos.append((consulta, n, desde))
        if self.error:
            raise self.error
        return self.articulos[:n]


def _error_http(codigo):
    return httpx.HTTPStatusError(
        "fallo",
        request=httpx.Request("GET", "https://api.ejemplo.org/?api_key=secreta"),
        response=httpx.Response(codigo),
    )


@pytest.fixture
def fuentes(monkeypatch, hacer_articulo):
    """OpenAlex y Crossref comparten un DOI; arXiv falla."""
    comun = hacer_articulo()
    fuentes = {
        "OpenAlex": FuenteFalsa([comun, hacer_articulo(doi="10.1/a", citations=None)]),
        "Crossref": FuenteFalsa([comun, hacer_articulo(doi="10.1/b", citations=7)]),
        "arXiv": FuenteFalsa(error=_error_http(503)),
        "PANGAEA": FuenteFalsa(error=httpx.ConnectError("sin red")),
    }
    monkeypatch.setattr("litmar.configuracion.crear_fuente", lambda nombre: fuentes[nombre])
    monkeypatch.delenv("ZOTERO_USER_ID", raising=False)
    monkeypatch.delenv("ZOTERO_GROUP_ID", raising=False)
    return fuentes


# --- /salud y /fuentes -------------------------------------------------------------


def test_salud():
    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ok"


def test_fuentes_solo_las_disponibles(monkeypatch):
    monkeypatch.delenv("ZOTERO_USER_ID", raising=False)
    monkeypatch.delenv("ZOTERO_GROUP_ID", raising=False)
    ids = [f["id"] for f in cliente.get("/fuentes").json()]
    assert "zotero" not in ids
    assert {"id": "europepmc", "name": "Europe PMC"} in cliente.get("/fuentes").json()

    monkeypatch.setenv("ZOTERO_USER_ID", "123")
    assert "zotero" in [f["id"] for f in cliente.get("/fuentes").json()]


# --- /buscar -----------------------------------------------------------------------


def test_buscar_en_varias_fuentes_sin_duplicar(fuentes):
    respuesta = cliente.get(
        "/buscar",
        params={"consulta": "posidonia", "fuente": ["openalex", "Crossref"], "n": 2, "desde": 2020},
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["query"] == "posidonia"
    comun = fuentes["Crossref"].articulos[0].doi
    assert [a["doi"] for a in datos["articles"]] == [comun, "10.1/a", "10.1/b"]
    assert datos["errors"] == [] and datos["failed"] == []
    # Los mismos campos que Articulo; null si la fuente no da las citas.
    assert set(datos["articles"][0]) == {
        "title", "authors", "year", "doi", "journal", "abstract", "citations"
    }  # fmt: skip
    assert datos["articles"][1]["citations"] is None
    # Llama a buscar_en_fuentes con lo pedido.
    assert fuentes["OpenAlex"].pedidos == [("posidonia", 2, 2020)]


def test_buscar_por_defecto_en_openalex(fuentes):
    respuesta = cliente.get("/buscar", params={"consulta": "posidonia"})

    assert respuesta.status_code == 200
    assert fuentes["OpenAlex"].pedidos == [("posidonia", 10, None)]
    assert fuentes["Crossref"].pedidos == []


def test_si_falla_una_fuente_devuelve_las_demas_y_el_error(fuentes):
    respuesta = cliente.get("/buscar", params={"consulta": "x", "fuente": ["openalex", "arxiv"]})

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos["articles"]) == 2
    assert datos["failed"] == ["arXiv"]
    assert datos["errors"] == ["arXiv respondió con HTTP 503."]


def test_si_fallan_todas_las_fuentes_da_502_sin_la_peticion(fuentes):
    respuesta = cliente.get("/buscar", params={"consulta": "x", "fuente": ["arxiv", "pangaea"]})

    assert respuesta.status_code == 502
    detalle = respuesta.json()["detail"]
    assert "arXiv respondió con HTTP 503." in detalle
    assert "PANGAEA: no se pudo conectar" in detalle
    assert "secreta" not in respuesta.text


@pytest.mark.parametrize(
    "parametros",
    [
        {"consulta": "x", "n": 0},
        {"consulta": "x", "n": 51},
        {"consulta": "x", "n": "muchos"},
        {"consulta": "   "},
        {},
        {"consulta": "x", "fuente": "nada"},
        {"consulta": "x", "fuente": "zotero"},  # sin ZOTERO_USER_ID en el servidor
        {"consulta": "x", "desde": "ayer"},
    ],
)
def test_buscar_con_datos_invalidos_da_422(fuentes, parametros):
    respuesta = cliente.get("/buscar", params=parametros)

    assert respuesta.status_code == 422
    assert all(not f.pedidos for f in fuentes.values())  # no llega a buscar


# --- /revisiones -------------------------------------------------------------------


class ModeloFalso:
    """Para el flujo: plan y resúmenes estructurados, y un informe de texto."""

    def __init__(self, informe):
        self.informe = informe

    def with_structured_output(self, esquema, **opciones):
        return self

    def invoke(self, mensajes):
        from langchain_core.messages import AIMessage

        from litmar.flujo import Plan
        from litmar.resumen import ResumenArticulo

        texto = str(mensajes[0][1])
        if "documentalista" in texto:  # planificar
            return Plan(queries=["redes neuronales"])
        if "resume artículos" in texto:  # resumir
            return ResumenArticulo(
                objective="O", method="M", findings=["H"], relevance=4, limitations="L"
            )
        return AIMessage(content=self.informe)  # sintetizar


@pytest.fixture
def con_modelo(monkeypatch, fuentes, tmp_path):
    modelo = ModeloFalso("Según [doi:10.1/a] y [doi:10.9999/inventado].")
    monkeypatch.setattr("litmar.llm.crear_modelo", lambda: modelo)
    monkeypatch.chdir(tmp_path)  # para comprobar que no se escribe nada en disco
    return modelo


def test_revision_con_el_flujo(con_modelo, tmp_path):
    respuesta = cliente.post(
        "/revisiones", json={"question": "  ¿Sirven las redes?  ", "sources": ["openalex"]}
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["question"] == "¿Sirven las redes?" and datos["mode"] == "flujo"
    assert datos["queries"] == ["redes neuronales"]
    # Solo cita lo real: el DOI inventado queda marcado y fuera del BibTeX.
    assert "[doi:10.1/a]" in datos["report"] and "[cita no verificada]" in datos["report"]
    assert [a["doi"] for a in datos["cited"]] == ["10.1/a"]
    assert "doi = {10.1/a}" in datos["bibtex"] and "10.9999" not in datos["bibtex"]
    assert any("reescrituras" in aviso for aviso in datos["warnings"])
    assert list(tmp_path.iterdir()) == []  # ni informe ni BibTeX en disco


def test_revision_con_el_agente(con_modelo, monkeypatch, hacer_articulo):
    articulo = hacer_articulo(doi="10.1/a")
    llamadas = []

    def revisar_falso(modelo, pregunta, *, fuentes, n, desde, idioma, mostrar):
        llamadas.append((pregunta, fuentes, n, desde, idioma))
        return {
            "question": pregunta,
            "queries": ["redes"],
            "selected": [articulo],
            "report": "Según [doi:10.1/a].",
            "cited": ["10.1/a"],
            "warnings": [],
        }

    monkeypatch.setattr("litmar.agente.revisar", revisar_falso)

    respuesta = cliente.post(
        "/revisiones",
        json={
            "question": "¿Sirven las redes?",
            "mode": "agente",
            "sources": ["openalex", "europepmc", "openalex"],
            "n": 4,
            "since": 2020,
            "language": "en",
        },
    )

    assert respuesta.status_code == 200
    assert llamadas == [("¿Sirven las redes?", ["OpenAlex", "Europe PMC"], 4, 2020, "en")]
    datos = respuesta.json()
    assert datos["mode"] == "agente"
    assert datos["language"] == "en"
    assert [a["doi"] for a in datos["cited"]] == ["10.1/a"]
    assert "@article" in datos["bibtex"]


def test_revision_con_las_fuentes_por_defecto(con_modelo, monkeypatch):
    llamadas = []

    def revisar_falso(modelo, pregunta, *, fuentes, n, desde, idioma, mostrar):
        llamadas.append((fuentes, n, desde, idioma))
        return {"question": pregunta, "report": "Sin artículos.", "cited": [], "warnings": []}

    monkeypatch.setattr("litmar.flujo.revisar", revisar_falso)

    assert cliente.post("/revisiones", json={"question": "x"}).status_code == 200
    assert llamadas == [(["OpenAlex", "Europe PMC"], 6, None, "es")]


def test_revision_en_japones_localiza_el_informe(con_modelo, monkeypatch):
    def revisar_falso(modelo, pregunta, *, fuentes, n, desde, idioma, mostrar):
        assert idioma == "ja"
        return {
            "question": pregunta,
            "queries": [],
            "report": "日本語のレポート。",
            "cited": [],
            "warnings": [],
        }

    monkeypatch.setattr("litmar.flujo.revisar", revisar_falso)
    respuesta = cliente.post(
        "/revisiones",
        json={"question": "質問", "sources": ["openalex"], "language": "ja"},
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["language"] == "ja"
    assert "日本語のレポート" in datos["report"]
    assert "## 参考文献" not in datos["report"]


def test_revision_rechaza_un_idioma_no_admitido(con_modelo):
    respuesta = cliente.post("/revisiones", json={"question": "x", "language": "fr"})

    assert respuesta.status_code == 422


def test_revision_sin_modelo_da_503_y_dice_que_poner_en_el_env(monkeypatch, fuentes):
    for variable in ("LITMAR_MODELO", "GOOGLE_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(variable, raising=False)

    respuesta = cliente.post("/revisiones", json={"question": "¿Sirven las redes?"})

    assert respuesta.status_code == 503
    assert "LITMAR_MODELO=proveedor:modelo" in respuesta.json()["detail"]


def test_si_el_modelo_falla_da_502_sin_su_mensaje(con_modelo, monkeypatch):
    def revisar_que_falla(*args, **kwargs):
        raise RuntimeError("429 para la clave sk-secreta")

    monkeypatch.setattr("litmar.flujo.revisar", revisar_que_falla)

    respuesta = cliente.post("/revisiones", json={"question": "¿Sirven las redes?"})

    assert respuesta.status_code == 502
    assert "RuntimeError" in respuesta.json()["detail"]
    assert "secreta" not in respuesta.text


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"question": "   "},
        {"question": "x", "mode": "otro"},
        {"question": "x", "n": 0},
        {"question": "x", "n": 11},  # más que MAX_SELECCIONADOS
        {"question": "x", "sources": []},
        {"question": "x", "sources": ["nada"]},
        {},
    ],
)
def test_revision_con_datos_invalidos_da_422(con_modelo, monkeypatch, cuerpo):
    monkeypatch.setattr("litmar.flujo.revisar", lambda *a, **k: pytest.fail("no debe revisar"))

    assert cliente.post("/revisiones", json=cuerpo).status_code == 422


def test_la_documentacion_describe_las_rutas():
    rutas = cliente.get("/openapi.json").json()["paths"]

    assert set(rutas) == {"/salud", "/fuentes", "/buscar", "/revisiones"}
    assert "502" in rutas["/buscar"]["get"]["responses"]
    assert {"502", "503", "422"} <= set(rutas["/revisiones"]["post"]["responses"])


# --- La página web en / ---------------------------------------------------------


def test_la_api_sirve_la_pagina_en_la_raiz():
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "<title>litmar</title>" in respuesta.text
    assert 'value="pt-BR"' in respuesta.text
    assert 'value="en"' in respuesta.text
    assert 'value="ja"' in respuesta.text
    assert 'language: $("idioma").value' in respuesta.text


def test_la_pagina_solo_usa_rutas_del_contrato_y_relativas():
    import re

    pagina = cliente.get("/").text
    rutas = set(re.findall(r'pedir\(`?"?(/[a-z]+)', pagina))
    contrato = set(cliente.get("/openapi.json").json()["paths"])

    assert rutas == {"/fuentes", "/buscar", "/revisiones"}
    assert rutas <= contrato
    # Sin la dirección del servidor: funciona en cualquier host y puerto.
    assert "127.0.0.1" not in pagina and "localhost" not in pagina
    assert not re.search(r"fetch\(\s*[`'\"]https?:", pagina)


# --- litmar servir -----------------------------------------------------------------


def test_servir_arranca_uvicorn(monkeypatch):
    llamadas = []
    monkeypatch.setattr("uvicorn.run", lambda app, **opciones: llamadas.append((app, opciones)))

    assert cli.main(["servir"]) == 0
    assert cli.main(["servir", "--host", "0.0.0.0", "--puerto", "9000", "--recargar"]) == 0
    assert llamadas == [
        ("litmar.api:app", {"host": "127.0.0.1", "port": 8000, "reload": False}),
        ("litmar.api:app", {"host": "0.0.0.0", "port": 9000, "reload": True}),
    ]


def test_servir_con_puerto_invalido():
    with pytest.raises(SystemExit):
        cli.main(["servir", "--puerto", "0"])
