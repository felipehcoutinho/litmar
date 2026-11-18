from litmar.articulo import Articulo
from litmar.biblioteca import Biblioteca
from litmar.resumen import ResumenArticulo, resumir

__all__ = ["Articulo", "Biblioteca", "ResumenArticulo", "main", "resumir"]


def main() -> None:
    from dotenv import find_dotenv, load_dotenv

    from litmar.cli import main as ejecutar

    # Lee el .env del directorio actual (o de uno superior). Las variables que
    # ya estén definidas en el entorno tienen prioridad.
    load_dotenv(find_dotenv(usecwd=True))

    raise SystemExit(ejecutar())
