import pytest
from pydantic import ValidationError

from litmar import ResumenArticulo, resumir


class CadenaFalsa:
    def __init__(self, schema: type[ResumenArticulo], salida: dict[str, object]) -> None:
        self.schema = schema
        self.salida = salida
        self.prompt = ""

    def invoke(self, input: str) -> ResumenArticulo:
        self.prompt = input
        return self.schema.model_validate(self.salida)


class ModeloFalso:
    def __init__(self, salida: dict[str, object]) -> None:
        self.salida = salida
        self.esquemas: list[type[ResumenArticulo]] = []
        self.cadena: CadenaFalsa | None = None

    def with_structured_output(self, schema: type[ResumenArticulo]) -> CadenaFalsa:
        self.esquemas.append(schema)
        self.cadena = CadenaFalsa(schema, self.salida)
        return self.cadena


@pytest.fixture
def salida_resumen() -> dict[str, object]:
    return {
        "objetivo": "Evaluar el efecto del calentamiento.",
        "metodo": "Experimento de laboratorio.",
        "hallazgos": "La tasa de crecimiento disminuyó.",
        "relevancia": 4,
        "limitaciones": "Duración breve.",
    }


def test_resumir_devuelve_el_resumen_estructurado(
    hacer_articulo, salida_resumen: dict[str, object]
) -> None:
    articulo = hacer_articulo(abstract="Un estudio sobre el calentamiento.")
    modelo = ModeloFalso(salida_resumen)

    resultado = resumir(articulo, "¿Cómo afecta el calentamiento?", modelo)

    assert isinstance(resultado, ResumenArticulo)
    assert resultado.relevancia == 4
    assert modelo.esquemas == [ResumenArticulo]
    assert modelo.cadena is not None
    assert "¿Cómo afecta el calentamiento?" in modelo.cadena.prompt
    assert articulo.abstract in modelo.cadena.prompt


def test_resumir_sin_resumen_no_llama_al_modelo(
    hacer_articulo, salida_resumen: dict[str, object]
) -> None:
    modelo = ModeloFalso(salida_resumen)

    with pytest.raises(ValueError, match="sin resumen"):
        resumir(hacer_articulo(abstract="  "), "Pregunta", modelo)

    assert modelo.esquemas == []


@pytest.mark.parametrize("relevancia", [0, 6])
def test_resumen_rechaza_relevancia_fuera_de_escala(
    salida_resumen: dict[str, object], relevancia: int
) -> None:
    datos = {**salida_resumen, "relevancia": relevancia}

    with pytest.raises(ValidationError):
        ResumenArticulo.model_validate(datos)
