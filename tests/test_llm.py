import pytest
from langchain_core.rate_limiters import InMemoryRateLimiter

from litmar.llm import crear_modelo


def test_crear_modelo_usa_la_configuracion_de_anthropic(monkeypatch) -> None:
    monkeypatch.setenv("LITMAR_MODELO", "anthropic:claude-sonnet-5-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-falsa")
    llamadas = []

    def init_falso(*, model: str, **kwargs: object) -> object:
        resultado = object()
        llamadas.append((model, kwargs, resultado))
        return resultado

    monkeypatch.setattr("litmar.llm.init_chat_model", init_falso)

    modelo = crear_modelo()

    assert modelo is llamadas[0][2]
    assert llamadas[0][0] == "anthropic:claude-sonnet-5-5"
    assert llamadas[0][1] == {}


def test_crear_modelo_limita_y_comparte_las_llamadas_de_gemini(monkeypatch) -> None:
    monkeypatch.setenv("LITMAR_MODELO", "google_genai:gemini-3.8-flash")
    monkeypatch.setenv("GOOGLE_API_KEY", "clave-falsa")
    llamadas = []

    def init_falso(*, model: str, **kwargs: object) -> object:
        resultado = object()
        llamadas.append((model, kwargs, resultado))
        return resultado

    monkeypatch.setattr("litmar.llm.init_chat_model", init_falso)

    primer_modelo = crear_modelo()
    segundo_modelo = crear_modelo()

    assert primer_modelo is llamadas[0][2]
    assert segundo_modelo is llamadas[1][2]
    limitador = llamadas[0][1]["rate_limiter"]
    assert isinstance(limitador, InMemoryRateLimiter)
    assert limitador.requests_per_second == pytest.approx(10 / 60)
    assert limitador.max_bucket_size == 1
    assert llamadas[1][1]["rate_limiter"] is limitador


@pytest.mark.parametrize(
    ("configuracion", "variable"),
    [
        ("google_genai:gemini-3.8-flash", "GOOGLE_API_KEY"),
        ("anthropic:claude-sonnet-5-5", "ANTHROPIC_API_KEY"),
    ],
)
def test_crear_modelo_indica_como_configurar_la_clave(
    monkeypatch, configuracion: str, variable: str
) -> None:
    monkeypatch.setenv("LITMAR_MODELO", configuracion)
    monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ValueError, match=rf"{variable}.*\.env"):
        crear_modelo()


def test_crear_modelo_indica_como_configurar_litmar_modelo(monkeypatch) -> None:
    monkeypatch.delenv("LITMAR_MODELO", raising=False)

    with pytest.raises(ValueError, match=r"LITMAR_MODELO.*\.env"):
        crear_modelo()


def test_crear_modelo_rechaza_configuracion_sin_proveedor(monkeypatch) -> None:
    monkeypatch.setenv("LITMAR_MODELO", "modelo-sin-proveedor")

    with pytest.raises(ValueError, match="proveedor:modelo"):
        crear_modelo()
