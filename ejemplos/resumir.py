"""Busca y resume tres artículos sobre bacteriófagos de Nitrospira."""

import sys

from dotenv import find_dotenv, load_dotenv

from litmar.busqueda import buscar_en_fuentes
from litmar.llm import crear_modelo
from litmar.resumen import resumir

CONSULTA = "Nitrospira bacteriophage"
PREGUNTA = "¿Qué bacteriófagos infectan a Nitrospira y cómo afectan a su hospedador?"
FUENTES = ("OpenAlex", "Europe PMC")
RESULTADOS_POR_FUENTE = 10
ARTICULOS_A_RESUMIR = 3


def main() -> None:
    """Busca candidatos con resumen y resume los tres primeros."""
    resultado = buscar_en_fuentes(CONSULTA, FUENTES, n=RESULTADOS_POR_FUENTE)
    for error in resultado.errors:
        print(f"Aviso: {error}", file=sys.stderr)

    articulos = [articulo for articulo in resultado.library if articulo.abstract.strip()][
        :ARTICULOS_A_RESUMIR
    ]
    if len(articulos) < ARTICULOS_A_RESUMIR:
        raise SystemExit(
            f"Solo se encontraron {len(articulos)} artículos con resumen; "
            f"se necesitan {ARTICULOS_A_RESUMIR}."
        )

    modelo = crear_modelo()
    for numero, articulo in enumerate(articulos, start=1):
        resumen = resumir(articulo, PREGUNTA, modelo)
        print(f"\n{numero}. {articulo.title} ({articulo.year})")
        print(f"DOI: https://doi.org/{articulo.doi}")
        print(f"Objetivo: {resumen.objetivo}")
        print(f"Método: {resumen.metodo}")
        print(f"Hallazgos: {resumen.hallazgos}")
        print(f"Relevancia: {resumen.relevancia}/5")
        print(f"Limitaciones: {resumen.limitaciones}")


if __name__ == "__main__":
    load_dotenv(find_dotenv(usecwd=True))
    main()
