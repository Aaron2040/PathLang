"""
lexer_test.py — PathLang
Muestra la lista de tokens reconocidos por el Analizador Léxico
para una o varias entradas de prueba.

Uso:
    python lexer_test.py <archivo.txt>
    python lexer_test.py tests/test_valido_01.txt
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gen'))

from antlr4 import InputStream, CommonTokenStream

from antlr4.error.ErrorListener import ErrorListener
from PathLangLexer import PathLangLexer
from PathLangParser import PathLangParser   # solo para obtener los nombres de tokens


# Mapa de número de tipo → nombre del token (leído del vocabulario ANTLR)
def build_token_names():
    """Construye un dict {tipo_int: 'NOMBRE_TOKEN'} a partir del vocabulario del parser."""
    names = {}
    vocab = PathLangParser.literalNames + PathLangParser.symbolicNames
    # ANTLR pone None en algunos slots; los saltamos
    for i, name in enumerate(PathLangParser.symbolicNames):
        if name:
            names[i] = name
    return names


class LexerErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errores = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errores.append(f"  [ERROR LÉXICO] línea {line}:{column} → {msg}")


def analizar_lexico(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"  Archivo no encontrado: {path}")
        return

    input_stream = InputStream(source)
    lexer        = PathLangLexer(input_stream)

    error_listener = LexerErrorListener()
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    token_stream = CommonTokenStream(lexer)
    token_stream.fill()                     # fuerza el tokenizado completo
    tokens = token_stream.tokens

    vocab = PathLangLexer.ruleNames          # nombres de las reglas léxicas (0-indexed)

    print("=" * 70)
    print(f"  Análisis Léxico: {path}")
    print("=" * 70)
    print(f"  {'#':<4} {'TOKEN (tipo)':<22} {'LEXEMA':<28} LÍNEA:COL")
    print("-" * 70)

    count = 0
    for tok in tokens:
        if tok.type == -1:          # EOF — no lo mostramos
            break
        tipo = tok.type
        # Nombre del token: puede venir del symbolicName del lexer
        # (índices coinciden con el orden de definición en el .g4)
        try:
            nombre = PathLangLexer.symbolicNames[tipo]
            if not nombre:
                nombre = f"TIPO_{tipo}"
        except IndexError:
            nombre = f"TIPO_{tipo}"

        lexema = repr(tok.text)
        count += 1
        print(f"  {count:<4} {nombre:<22} {lexema:<28} {tok.line}:{tok.column}")

    print("-" * 70)
    print(f"  Total tokens reconocidos: {count}")

    if error_listener.errores:
        print()
        print("  ⚠ Errores léxicos:")
        for err in error_listener.errores:
            print(err)
        print(f"  Resultado: INVÁLIDO — {len(error_listener.errores)} error(es) léxico(s).")
    else:
        print("  Resultado: VÁLIDO — todos los tokens reconocidos correctamente.")
    print("=" * 70)
    print()


def main():
    if len(sys.argv) < 2:
        # Sin argumento: corre todos los tests
        import glob, os
        archivos = sorted(glob.glob("tests/test_valido_*.txt")) + \
                   sorted(glob.glob("tests/test_error_*.txt"))
        if not archivos:
            print("Uso: python lexer_test.py <archivo.txt>")
            return
        print(f"\nEjecutando análisis léxico sobre {len(archivos)} archivos...\n")
        for arch in archivos:
            analizar_lexico(arch)
    else:
        for path in sys.argv[1:]:
            analizar_lexico(path)


if __name__ == "__main__":
    main()
