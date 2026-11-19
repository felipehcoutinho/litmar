"""Tests de resumir() con un modelo falso: sin clave, sin red y sin gastar tokens."""

import pytest
from pydantic import ValidationError

from litmar.resumen import ResumenArticulo, resumir

RESUMEN_FALSO = ResumenArticulo(
    objective="Clasificar textos con redes neuronales.",
    method="Redes neuronales profundas sobre un corpus de textos.",
    findings=["Las redes profundas mejoran la clasificación."],
    relevance=4,
    limitations="No consta en el resumen.",
)


class ModeloFalso:
    """Imita la parte de un modelo de chat de LangChain que usa resumir().

    Devuelve siempre la misma respuesta y apunta con qué se le llamó.
    """

    def __init__(self, respuesta=RESUMEN_FALSO):
        self.respuesta = respuesta
        self.esquema = None
        self.opciones = None
        self.llamadas = []

    def with_structured_output(self, esquema, **opciones):
        self.esquema = esquema
        self.opciones = opciones
        return self

    def invoke(self, mensajes):
        self.llamadas.append(mensajes)
        return self.respuesta


def texto_enviado(modelo):
    """Todo el texto de la única llamada que recibió el modelo."""
    assert len(modelo.llamadas) == 1
    return "\n".join(contenido for _, contenido in modelo.llamadas[0])


def test_devuelve_el_objeto_estructurado(hacer_articulo):
    modelo = ModeloFalso()

    resumen = resumir(hacer_articulo(), "¿Sirven las redes neuronales?", modelo)

    assert resumen == RESUMEN_FALSO
    assert modelo.esquema is ResumenArticulo
    assert modelo.opciones == {"method": "json_schema"}


def test_envia_pregunta_titulo_y_resumen(hacer_articulo):
    modelo = ModeloFalso()
    articulo = hacer_articulo(abstract="Estudiamos 300 praderas de Posidonia.")

    resumir(articulo, "¿Cuánto carbono almacena Posidonia?", modelo)

    texto = texto_enviado(modelo)
    assert "¿Cuánto carbono almacena Posidonia?" in texto
    assert articulo.title in texto
    assert "Estudiamos 300 praderas de Posidonia." in texto


@pytest.mark.parametrize(
    ("idioma", "instruccion"),
    [
        ("pt-BR", "português do Brasil"),
        ("en", "exclusively in English"),
        ("ja", "日本語のみ"),
    ],
)
def test_indica_al_modelo_el_idioma_seleccionado(hacer_articulo, idioma, instruccion):
    modelo = ModeloFalso()

    resumir(hacer_articulo(), "question", modelo, idioma=idioma)

    assert instruccion in texto_enviado(modelo)


@pytest.mark.parametrize("abstract", ["", "   \n"])
def test_sin_resumen_no_llama_al_modelo(hacer_articulo, abstract):
    modelo = ModeloFalso()

    assert resumir(hacer_articulo(abstract=abstract), "pregunta", modelo) is None
    assert modelo.llamadas == []


def test_todos_los_campos_tienen_descripcion():
    # El modelo lee las descripciones: un campo sin ella es un campo sin instrucciones.
    for nombre, campo in ResumenArticulo.model_fields.items():
        assert campo.description, f"el campo {nombre} no tiene descripción"


@pytest.mark.parametrize("relevancia", [0, 6])
def test_relevancia_fuera_de_rango_no_es_valida(relevancia):
    datos = RESUMEN_FALSO.model_dump() | {"relevance": relevancia}

    with pytest.raises(ValidationError):
        ResumenArticulo(**datos)
