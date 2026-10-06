import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gen'))

from antlr4 import *

from PathLangLexer import PathLangLexer
from PathLangParser import PathLangParser
from PathLangVisitor import PathLangVisitor
from antlr4.error.ErrorListener import ErrorListener
from tabla_simbolos import TablaSimbolos, TipoSimbolo


# =============================================================================
# Error Listeners — separados para léxico y sintáctico
# =============================================================================
class LexerErrorListener(ErrorListener):
    """Captura errores del analizador LÉXICO (token no reconocido)."""
    def __init__(self):
        super().__init__()
        self.has_errors = False

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.has_errors = True
        print(f"  [Error Léxico, línea {line}:{column}] {msg}")


class ParserErrorListener(ErrorListener):
    """Captura errores del analizador SINTÁCTICO (estructura inválida)."""
    def __init__(self):
        super().__init__()
        self.has_errors = False

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.has_errors = True
        token_txt = f"'{offendingSymbol.text}'" if offendingSymbol else ""
        print(f"  [Error Sintáctico, línea {line}:{column}] {msg}")


# =============================================================================
# Analizador Semántico — Visitor completo con Tabla de Símbolos
#
# Errores implementados:
#   E1 — Uso de nombre no declarado
#   E2 — Redeclaración en el mismo ámbito
#   E3 — Tipo de símbolo incorrecto (ej: usar un nodo como grafo)
# =============================================================================
class AnalizadorSemantico(PathLangVisitor):

    def __init__(self, tabla: TablaSimbolos):
        self.tabla = tabla
        # Registra en qué grafo estamos actualmente (para anidar el ámbito)
        self._grafo_actual: str | None = None

    # ------------------------------------------------------------------
    # Declaración de grafo
    # ------------------------------------------------------------------
    def visitDeclGrafo(self, ctx: PathLangParser.DeclGrafoContext):
        nombre = ctx.ID().getText()
        dirigido = ctx.dirigidoOpt().DIRIGIDO() is not None

        self.tabla.declarar(
            nombre   = nombre,
            tipo     = TipoSimbolo.GRAFO,
            linea    = ctx.start.line,
            columna  = ctx.start.column,
            atributos = {"dirigido": str(dirigido)}
        )

        # Abrimos ámbito propio del grafo para nodos y aristas
        self._grafo_actual = nombre
        self.tabla.entrar_ambito(f"grafo:{nombre}")
        resultado = self.visitChildren(ctx)
        self.tabla.salir_ambito()
        self._grafo_actual = None
        return resultado

    # ------------------------------------------------------------------
    # Declaración de nodo
    # ------------------------------------------------------------------
    def visitDeclNodo(self, ctx: PathLangParser.DeclNodoContext):
        nombre = ctx.ID().getText()
        coords  = ctx.coord()

        # Construye el valor de las coordenadas extrayendo el texto
        def coord_val(c):
            return "-" + c.NUM().getText() if c.MENOS() else c.NUM().getText()

        self.tabla.declarar(
            nombre   = nombre,
            tipo     = TipoSimbolo.NODO,
            linea    = ctx.start.line,
            columna  = ctx.start.column,
            atributos = {
                "lat": coord_val(coords[0]),
                "lon": coord_val(coords[1]),
                "grafo": self._grafo_actual or "?",
            }
        )
        return self.visitChildren(ctx)

    # ------------------------------------------------------------------
    # Declaración de arista
    # ------------------------------------------------------------------
    def visitDeclArista(self, ctx: PathLangParser.DeclAristaContext):
        # arista ID FLECHA ID ':' peso UNIDAD tipoOpt ';'
        ids   = ctx.ID()          # [0]=nodo origen, [1]=nodo destino
        nodo_origen = ids[0].getText()
        nodo_destino  = ids[1].getText()
        flecha = ctx.FLECHA().getText()
        peso   = ctx.peso().NUM().getText()
        
        is_negative = ctx.peso().MENOS() is not None
        if is_negative:
            peso = "-" + peso
            self.tabla.errores.append(
                f"[E3] Error SEMÁNTICO (línea {ctx.start.line}): "
                f"Peso negativo en arista {nodo_origen} {flecha} {nodo_destino}: A* exige pesos >= 0"
            )

        unidad = ctx.UNIDAD().getText()

        # Verificar que el nodo origen está declarado
        sim_origen = self.tabla.resolver(
            nombre          = nodo_origen,
            linea           = ctx.start.line,
            tipos_esperados = [TipoSimbolo.NODO]
        )
        if sim_origen and sim_origen.atributos.get('grafo') != self._grafo_actual:
            self.tabla.errores.append(
                f"[E11] Error SEMÁNTICO (línea {ctx.start.line}): "
                f"El nodo '{nodo_origen}' no pertenece al grafo '{self._grafo_actual}'"
            )

        # Verificar que el nodo destino está declarado
        sim_destino = self.tabla.resolver(
            nombre          = nodo_destino,
            linea           = ctx.start.line,
            tipos_esperados = [TipoSimbolo.NODO]
        )
        if sim_destino and sim_destino.atributos.get('grafo') != self._grafo_actual:
            self.tabla.errores.append(
                f"[E11] Error SEMÁNTICO (línea {ctx.start.line}): "
                f"El nodo '{nodo_destino}' no pertenece al grafo '{self._grafo_actual}'"
            )

        # Atributo opcional 'tipo'
        tipo_via = None
        if ctx.tipoOpt().TIPO():
            tipo_via = ctx.tipoOpt().ID().getText()

        attrs = {
            "origen" : nodo_origen,
            "destino": nodo_destino,
            "flecha" : flecha,
            "peso"   : peso,
            "unidad" : unidad,
            "grafo"  : self._grafo_actual or "?",
        }
        if tipo_via:
            attrs["tipo_via"] = tipo_via

        # Generar un nombre único interno (anonimo) para que no haya colisión E9
        anon_name = f"__arista_{nodo_origen}_{nodo_destino}_{ctx.start.line}"

        self.tabla.declarar(
            nombre    = anon_name,
            tipo      = TipoSimbolo.ARISTA,
            linea     = ctx.start.line,
            columna   = ctx.start.column,
            atributos = attrs,
        )
        return self.visitChildren(ctx)

    # ------------------------------------------------------------------
    # Declaración de heurística
    # ------------------------------------------------------------------
    def visitDeclHeuristica(self, ctx: PathLangParser.DeclHeuristicaContext):
        ids = ctx.ID()            # [0]=nombre, [1]=param1, [2]=param2
        nombre = ids[0].getText()
        p1     = ids[1].getText()
        p2     = ids[2].getText()

        self.tabla.declarar(
            nombre    = nombre,
            tipo      = TipoSimbolo.HEURISTICA,
            linea     = ctx.start.line,
            columna   = ctx.start.column,
            atributos = {"param1": p1, "param2": p2},
        )

        # Ámbito local de la heurística para sus parámetros
        self.tabla.entrar_ambito(f"heuristica:{nombre}")
        self.tabla.declarar(p1, TipoSimbolo.VARIABLE, ctx.start.line)
        self.tabla.declarar(p2, TipoSimbolo.VARIABLE, ctx.start.line)
        resultado = self.visitChildren(ctx)
        self.tabla.salir_ambito()
        return resultado

    # ------------------------------------------------------------------
    # Declaración de regla
    # ------------------------------------------------------------------
    def visitDeclRegla(self, ctx: PathLangParser.DeclReglaContext):
        nombre = ctx.ID().getText()

        self.tabla.declarar(
            nombre    = nombre,
            tipo      = TipoSimbolo.REGLA,
            linea     = ctx.start.line,
            columna   = ctx.start.column,
        )

        self.tabla.entrar_ambito(f"regla:{nombre}")
        resultado = self.visitChildren(ctx)
        self.tabla.salir_ambito()
        return resultado

    # ------------------------------------------------------------------
    # Sentencias Iterativas (para cada ...)
    # ------------------------------------------------------------------
    def visitParaInstr(self, ctx: PathLangParser.ParaInstrContext):
        nombre_var = ctx.ID(0).getText()
        nombre_grafo = ctx.ID(1).getText()
        tipo_elem = ctx.tipoElemento().getText()

        # Verificar que el grafo iterado exista
        self.tabla.resolver(nombre_grafo, ctx.start.line, [TipoSimbolo.GRAFO])

        tipo_sim = TipoSimbolo.NODO if tipo_elem == 'nodo' else TipoSimbolo.ARISTA

        # Crear un ámbito local e inyectar la variable de iteración
        self.tabla.entrar_ambito(f"para:{nombre_var}")
        self.tabla.declarar(
            nombre    = nombre_var,
            tipo      = tipo_sim,
            linea     = ctx.start.line,
            columna   = ctx.start.column,
            atributos = {"grafo": nombre_grafo}
        )

        resultado = self.visitChildren(ctx)
        self.tabla.salir_ambito()
        return resultado

    # ------------------------------------------------------------------
    # Asignación — declara variables locales de regla o verifica atributos
    # ------------------------------------------------------------------
    def visitAsignacion(self, ctx: PathLangParser.AsignacionContext):
        nombre_var = ctx.acceso().ID().getText()
        atributo = None
        if ctx.acceso().atributoOpt().PUNTO():
            atributo = ctx.acceso().atributoOpt().atributo().getText()
            
        if atributo:
            # Es una asignación a un atributo (e.peso := ... o n.lat := ...)
            sim = self.tabla.resolver(nombre_var, ctx.start.line)
            if sim:
                if sim.tipo == TipoSimbolo.NODO:
                    if atributo in ['lat', 'lon']:
                        self.tabla.errores.append(
                            f"[E7] Error SEMÁNTICO (línea {ctx.start.line}): "
                            f"'{nombre_var}.{atributo}' es inmutable: el nodo no se puede modificar"
                        )
                    else:
                        self.tabla.errores.append(
                            f"[E8] Error SEMÁNTICO (línea {ctx.start.line}): "
                            f"El nodo '{nombre_var}' no tiene el atributo '{atributo}'"
                        )
                elif sim.tipo == TipoSimbolo.ARISTA:
                    if atributo not in ['peso', 'tipo']:
                        self.tabla.errores.append(
                            f"[E8] Error SEMÁNTICO (línea {ctx.start.line}): "
                            f"La arista '{nombre_var}' no tiene el atributo '{atributo}'"
                        )
        else:
            # Si la variable no existe en el ámbito actual, la declaramos
            if self.tabla.ambito_actual.buscar_local(nombre_var) is None:
                self.tabla.declarar(
                    nombre    = nombre_var,
                    tipo      = TipoSimbolo.VARIABLE,
                    linea     = ctx.start.line,
                    columna   = ctx.start.column,
                )
        return self.visitChildren(ctx)

    # ------------------------------------------------------------------
    # Sentencia buscar
    # ------------------------------------------------------------------
    def visitBusqueda(self, ctx: PathLangParser.BusquedaContext):
        # buscar ruta ID[0] desde ID[1] hasta ID[2] en ID[3] usando ID[4] ...
        ids = ctx.ID()
        nombre_ruta  = ids[0].getText()
        nodo_origen  = ids[1].getText()
        nodo_destino = ids[2].getText()
        nombre_grafo = ids[3].getText()
        heuristica   = ids[4].getText()

        linea = ctx.start.line

        # Verificar que el grafo fue declarado
        self.tabla.resolver(nombre_grafo, linea, [TipoSimbolo.GRAFO])

        # Verificar nodo origen y destino (deben estar en algún ámbito visible)
        sim_origen = self.tabla.resolver(nodo_origen,  linea, [TipoSimbolo.NODO])
        sim_destino = self.tabla.resolver(nodo_destino, linea, [TipoSimbolo.NODO])
        
        if sim_origen and sim_origen.atributos.get('grafo') != nombre_grafo:
            self.tabla.errores.append(
                f"[E5] Error SEMÁNTICO (línea {linea}): El nodo '{nodo_origen}' no pertenece al grafo '{nombre_grafo}'"
            )
        if sim_destino and sim_destino.atributos.get('grafo') != nombre_grafo:
            self.tabla.errores.append(
                f"[E5] Error SEMÁNTICO (línea {linea}): El nodo '{nodo_destino}' no pertenece al grafo '{nombre_grafo}'"
            )

        # Verificar heurística
        self.tabla.resolver(heuristica, linea, [TipoSimbolo.HEURISTICA])

        # Verificar regla opcional (con ID)
        if ctx.conOpt().CON():
            nombre_regla = ctx.conOpt().ID().getText()
            self.tabla.resolver(nombre_regla, linea, [TipoSimbolo.REGLA])

        # Declarar la ruta resultante en el ámbito global
        attrs = {
            "desde"     : nodo_origen,
            "hasta"     : nodo_destino,
            "grafo"     : nombre_grafo,
            "heuristica": heuristica,
        }
        if ctx.horaOpt().A_LAS():
            hora_str = ctx.horaOpt().HORA().getText()
            attrs["hora"] = hora_str
            hh, mm = map(int, hora_str.split(':'))
            if hh > 23 or mm > 59:
                self.tabla.errores.append(
                    f"[E4] Error SEMÁNTICO (línea {linea}): Hora inválida '{hora_str}'"
                )

        self.tabla.declarar(
            nombre    = nombre_ruta,
            tipo      = TipoSimbolo.RUTA,
            linea     = linea,
            atributos = attrs,
        )
        return self.visitChildren(ctx)
        
    # ------------------------------------------------------------------
    # Condicion — valida hora en sentencias selectivas
    # ------------------------------------------------------------------
    def visitCondicion(self, ctx: PathLangParser.CondicionContext):
        if ctx.HORA_KW():
            horas = ctx.HORA()
            for h in horas:
                hora_str = h.getText()
                hh, mm = map(int, hora_str.split(':'))
                if hh > 23 or mm > 59:
                    self.tabla.errores.append(
                        f"[E4] Error SEMÁNTICO (línea {ctx.start.line}): Hora inválida '{hora_str}'"
                    )
        return self.visitChildren(ctx)

    # ------------------------------------------------------------------
    # mostrar — verifica que la ruta exista
    # ------------------------------------------------------------------
    def visitMostrar(self, ctx: PathLangParser.MostrarContext):
        nombre = ctx.ID().getText()
        self.tabla.resolver(nombre, ctx.start.line, [TipoSimbolo.RUTA])
        return self.visitChildren(ctx)


# =============================================================================
# MAIN
# =============================================================================
def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <archivo_de_prueba>")
        return

    input_file = sys.argv[1]

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{input_file}'")
        return

    print("=" * 80)
    print(f"  PathLang Compiler — Analizando: {input_file}")
    print("=" * 80)

    # ------------------------------------------------------------------
    # Fase 1a: Análisis LÉXICO
    # ------------------------------------------------------------------
    print("\n[ FASE 1 ] Análisis Léxico")
    print("-" * 80)

    input_stream   = InputStream(source)
    lexer          = PathLangLexer(input_stream)
    lexer_listener = LexerErrorListener()
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_listener)

    token_stream = CommonTokenStream(lexer)
    token_stream.fill()   # fuerza el tokenizado completo

    if lexer_listener.has_errors:
        print("\n  ✗ Resultado: INVÁLIDO — Errores léxicos.")
        print("=" * 80)
        return
    print("  ✓ Léxico: OK")

    # ------------------------------------------------------------------
    # Fase 1b: Análisis SINTÁCTICO
    # ------------------------------------------------------------------
    print("\n[ FASE 2 ] Análisis Sintáctico")
    print("-" * 80)

    # Rebobinar el token stream para el parser
    token_stream.reset()
    parser          = PathLangParser(token_stream)
    parser_listener = ParserErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(parser_listener)

    tree = parser.programa()

    if parser_listener.has_errors:
        print("\n  ✗ Resultado: INVÁLIDO — Errores sintácticos.")
        print("=" * 80)
        return
    print("  ✓ Sintáctico: OK")

    # ------------------------------------------------------------------
    # Fase 3: Análisis Semántico + Tabla de Símbolos
    # ------------------------------------------------------------------
    print("\n[ FASE 3 ] Análisis Semántico")
    print("-" * 80)

    tabla     = TablaSimbolos()
    semantico = AnalizadorSemantico(tabla)
    semantico.visit(tree)

    # Mostrar la tabla completa siempre
    tabla.imprimir()

    if tabla.errores:
        print(f"  ✗ Resultado: INVÁLIDO — {len(tabla.errores)} error(es) semántico(s).")
    else:
        print("  ✓ Semántico: OK")
        print()
        print("  ✓ Resultado final: PROGRAMA VÁLIDO")

    print("=" * 80)


if __name__ == "__main__":
    main()
