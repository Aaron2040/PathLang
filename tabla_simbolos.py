# =============================================================================
#  tabla_simbolos.py  —  PathLang Symbol Table
#  Implementación completa con:
#   - Tipos de símbolo: GRAFO, NODO, ARISTA, HEURISTICA, REGLA, RUTA, VARIABLE
#   - Atributos específicos por tipo (coordenadas, pesos, unidades, etc.)
#   - Gestión de ámbitos (scopes) anidados para detección de E2
#   - Registro global plano para resolución cruzada entre ámbitos (E1/E3)
#   - Registro de línea y columna de declaración
#   - Método de impresión formateada en tabla
# =============================================================================

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Tipos de símbolo reconocidos por PathLang
# ---------------------------------------------------------------------------
class TipoSimbolo(Enum):
    GRAFO      = "grafo"
    NODO       = "nodo"
    ARISTA     = "arista"
    HEURISTICA = "heuristica"
    REGLA      = "regla"
    RUTA       = "ruta"
    VARIABLE   = "variable"


# ---------------------------------------------------------------------------
# Entrada de la tabla de símbolos
# ---------------------------------------------------------------------------
@dataclass
class Simbolo:
    nombre:    str
    tipo:      TipoSimbolo
    ambito:    str                        # nombre del ámbito donde se declaró
    linea:     int                        # línea del código fuente
    columna:   int = 0                    # columna del código fuente
    atributos: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        attrs = ", ".join(f"{k}={v}" for k, v in self.atributos.items())
        return (f"[{self.tipo.value.upper():10}]  '{self.nombre}'"
                f"  ámbito='{self.ambito}'"
                f"  línea={self.linea}"
                + (f"  {{{attrs}}}" if attrs else ""))


# ---------------------------------------------------------------------------
# Ámbito (Scope)
# Usado exclusivamente para detectar redeclaraciones (E2) en el mismo nivel
# ---------------------------------------------------------------------------
class Ambito:
    def __init__(self, nombre: str, padre: Optional["Ambito"] = None):
        self.nombre = nombre
        self.padre  = padre
        self._simbolos: Dict[str, Simbolo] = {}

    def declarar(self, simbolo: Simbolo) -> bool:
        """Registra en este ámbito. Retorna False si ya existía (E2)."""
        if simbolo.nombre in self._simbolos:
            return False
        self._simbolos[simbolo.nombre] = simbolo
        return True

    def buscar_local(self, nombre: str) -> Optional[Simbolo]:
        """Solo en este ámbito, sin escalar."""
        return self._simbolos.get(nombre)

    def todos(self) -> List[Simbolo]:
        return list(self._simbolos.values())


# ---------------------------------------------------------------------------
# Tabla de Símbolos Principal
# ---------------------------------------------------------------------------
class TablaSimbolos:
    _SEP = "-" * 80

    def __init__(self):
        # ── Estructura de ámbitos (para E2: redeclaración) ──────────────
        self._global = Ambito("global")
        self._pila: List[Ambito] = [self._global]

        # ── Registro global plano (para E1/E3: resolución cruzada) ──────
        # Clave: nombre del símbolo → lista de Simbolo (puede haber en varios ámbitos)
        self._registro: Dict[str, List[Simbolo]] = {}

        self.errores: List[str] = []

    # ------------------------------------------------------------------
    # Gestión de ámbitos
    # ------------------------------------------------------------------
    @property
    def ambito_actual(self) -> Ambito:
        return self._pila[-1]

    def entrar_ambito(self, nombre: str):
        nuevo = Ambito(nombre, padre=self.ambito_actual)
        self._pila.append(nuevo)

    def salir_ambito(self):
        """Cierra el ámbito actual; los símbolos permanecen en el registro global."""
        if len(self._pila) > 1:
            self._pila.pop()

    # ------------------------------------------------------------------
    # Declaración de símbolo
    # ------------------------------------------------------------------
    def declarar(self, nombre: str, tipo: TipoSimbolo,
                 linea: int, columna: int = 0,
                 atributos: Dict[str, Any] = None) -> Optional[Simbolo]:
        """
        Declara un símbolo en el ámbito actual y en el registro global.
        Si ya existe en el MISMO ámbito → Error E2 (redeclaración).
        """
        atributos = atributos or {}
        nuevo = Simbolo(
            nombre    = nombre,
            tipo      = tipo,
            ambito    = self.ambito_actual.nombre,
            linea     = linea,
            columna   = columna,
            atributos = atributos,
        )
        # ── Verificar redeclaración en el ámbito actual (E2 / E9) ────────────
        ok = self.ambito_actual.declarar(nuevo)
        if not ok:
            existente = self.ambito_actual.buscar_local(nombre)
            if existente.tipo == tipo:
                self.errores.append(
                    f"[E2] Error SEMÁNTICO (línea {linea}): "
                    f"'{nombre}' ya fue declarado en la línea {existente.linea}"
                )
            else:
                self.errores.append(
                    f"[E9] Error SEMÁNTICO (línea {linea}): "
                    f"'{nombre}' ya fue declarado en la línea {existente.linea} como {existente.tipo.value}"
                )
            return None

        # ── Añadir al registro global plano ─────────────────────────────
        if nombre not in self._registro:
            self._registro[nombre] = []
        self._registro[nombre].append(nuevo)
        return nuevo

    # ------------------------------------------------------------------
    # Resolución de símbolo (búsqueda cruzada entre ámbitos)
    # ------------------------------------------------------------------
    def resolver(self, nombre: str, linea: int,
                 tipos_esperados: List[TipoSimbolo] = None) -> Optional[Simbolo]:
        """
        Busca un símbolo en el registro global (acceso cruzado entre ámbitos).
        Si no existe → Error E1.
        Si existe pero el tipo no coincide → Error E3.
        Si hay varios con el mismo nombre, prioriza el tipo esperado.
        """
        candidatos = self._registro.get(nombre, [])

        if not candidatos:
            if tipos_esperados and TipoSimbolo.HEURISTICA in tipos_esperados:
                self.errores.append(
                    f"[E6] Error SEMÁNTICO (línea {linea}): No existe la heurística '{nombre}'"
                )
            else:
                self.errores.append(
                    f"[E1] Error SEMÁNTICO (línea {linea}): No existe el nombre '{nombre}'"
                )
            return None

        # Si se especifican tipos esperados, filtra por ellos primero
        if tipos_esperados:
            filtrados = [s for s in candidatos if s.tipo in tipos_esperados]
            if not filtrados:
                self.errores.append(
                    f"[E10] Error SEMÁNTICO (línea {linea}): '{nombre}' es de categoría "
                    f"{candidatos[0].tipo.value}, se esperaba {tipos_esperados[0].value}"
                )
                return None
            return filtrados[0]

        # Sin restricción de tipo: devuelve el primero encontrado
        return candidatos[0]

    # ------------------------------------------------------------------
    # Utilidades de consulta
    # ------------------------------------------------------------------
    def todos_los_simbolos(self) -> List[Simbolo]:
        """Retorna todos los símbolos del registro global (todos los ámbitos)."""
        resultado = []
        vistos = set()
        for lista in self._registro.values():
            for sim in lista:
                key = (sim.ambito, sim.nombre)
                if key not in vistos:
                    vistos.add(key)
                    resultado.append(sim)
        return resultado

    def simbolos_por_tipo(self, tipo: TipoSimbolo) -> List[Simbolo]:
        return [s for s in self.todos_los_simbolos() if s.tipo == tipo]

    # ------------------------------------------------------------------
    # Impresión formateada en tabla
    # ------------------------------------------------------------------
    def imprimir(self):
        # Ordenar por: línea de declaración
        simbolos = sorted(self.todos_los_simbolos(), key=lambda s: s.linea)

        print()
        print("=" * 80)
        print("  TABLA DE SÍMBOLOS — PathLang")
        print("=" * 80)
        print(f"  {'TIPO':<12} {'NOMBRE':<22} {'ÁMBITO':<18} {'LÍNEA':<6} ATRIBUTOS")
        print(self._SEP)
        if not simbolos:
            print("  (vacía)")
        else:
            for s in simbolos:
                attrs = "  ".join(f"{k}={v}" for k, v in s.atributos.items())
                print(f"  {s.tipo.value:<12} {s.nombre:<22} {s.ambito:<18} "
                      f"{s.linea:<6} {attrs}")
        print("=" * 80)

        # Resumen por categoría
        counts: Dict[str, int] = {}
        for s in simbolos:
            counts[s.tipo.value] = counts.get(s.tipo.value, 0) + 1
        print("  RESUMEN:")
        for tipo_nombre, cant in sorted(counts.items()):
            print(f"    {tipo_nombre:<14}: {cant} símbolo(s)")
        print(f"    {'TOTAL':<14}: {len(simbolos)} símbolo(s)")
        print("=" * 80)

        if self.errores:
            print()
            print("  ERRORES SEMÁNTICOS DETECTADOS:")
            for i, err in enumerate(self.errores, 1):
                print(f"  {i:>2}. {err}")
            print("=" * 80)
        print()
