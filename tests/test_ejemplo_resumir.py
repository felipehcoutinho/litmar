from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from litmar import Biblioteca, ResumenArticulo
from litmar.busqueda import Resultado

_RUTA_EJEMPLO = Path(__file__).parents[1] / "ejemplos" / "resumir.py"
_ESPECIFICACION = spec_from_file_location("litmar_ejemplo_resumir", _RUTA_EJEMPLO)
assert _ESPECIFICACION is not None
assert _ESPECIFICACION.loader is not None
_EJEMPLO = module_from_spec(_ESPECIFICACION)
_ESPECIFICACION.loader.exec_module(_EJEMPLO)


def test_main_resume_tres_articulos_con_resumen(monkeypatch, hacer_articulo, capsys) -> None:
    articulos = [
        hacer_articulo(doi=f"10.1000/articulo-{numero}", abstract=abstract)
        for numero, abstract in enumerate(["", "Resumen 1", "Resumen 2", "Resumen 3", "Resumen 4"])
    ]
    resultado = Resultado(library=Biblioteca(articulos))
    busquedas = []
    modelo = object()
    resumen_falso = ResumenArticulo(
        objetivo="Objetivo",
        metodo="Método",
        hallazgos="Hallazgos",
        relevancia=4,
        limitaciones="Limitaciones",
    )
    resumidos = []

    def buscar(consulta: str, fuentes: tuple[str, ...], *, n: int) -> Resultado:
        busquedas.append((consulta, fuentes, n))
        return resultado

    def resumir_falso(articulo, pregunta: str, modelo_recibido: object) -> ResumenArticulo:
        resumidos.append((articulo, pregunta, modelo_recibido))
        return resumen_falso

    monkeypatch.setattr(_EJEMPLO, "buscar_en_fuentes", buscar)
    monkeypatch.setattr(_EJEMPLO, "crear_modelo", lambda: modelo)
    monkeypatch.setattr(_EJEMPLO, "resumir", resumir_falso)

    _EJEMPLO.main()

    assert busquedas == [(_EJEMPLO.CONSULTA, _EJEMPLO.FUENTES, _EJEMPLO.RESULTADOS_POR_FUENTE)]
    assert len(resumidos) == _EJEMPLO.ARTICULOS_A_RESUMIR
    assert all(
        pregunta == _EJEMPLO.PREGUNTA and modelo_recibido is modelo
        for _, pregunta, modelo_recibido in resumidos
    )
    assert "3. " in capsys.readouterr().out


def test_main_falla_si_no_hay_tres_articulos_con_resumen(monkeypatch, hacer_articulo) -> None:
    resultado = Resultado(library=Biblioteca([hacer_articulo(abstract="Solo uno")]))

    def buscar(consulta: str, fuentes: tuple[str, ...], *, n: int) -> Resultado:
        assert consulta and fuentes and n > 0
        return resultado

    monkeypatch.setattr(_EJEMPLO, "buscar_en_fuentes", buscar)
    monkeypatch.setattr(
        _EJEMPLO,
        "crear_modelo",
        lambda: pytest.fail("No debe crear un modelo si faltan artículos."),
    )

    with pytest.raises(SystemExit, match="se necesitan 3"):
        _EJEMPLO.main()
