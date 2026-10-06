grammar PathLang;

/* =========================================================================
   ANALIZADOR SINTÁCTICO (PARSER RULES)
   ========================================================================= */

programa: sentencias EOF ;

sentencias: sentencia sentencias 
          | /* vacío */ 
          ;

sentencia: declGrafo
         | declHeuristica
         | declRegla
         | busqueda
         | mostrar
         ;

/* --- GRAFOS Y NODOS --- */

declGrafo: GRAFO ID dirigidoOpt LLAVE_A elementos LLAVE_C ;

dirigidoOpt: DIRIGIDO 
           | /* vacío */ 
           ;

elementos: elemento elementos 
         | /* vacío */ 
         ;

elemento: declNodo 
        | declArista 
        ;

declNodo: NODO ID PAR_A coord COMA coord PAR_C PUNTOYCOMA ;

coord: MENOS NUM 
     | NUM 
     ;

declArista: ARISTA ID FLECHA ID DOSP peso UNIDAD tipoOpt PUNTOYCOMA ;

peso: MENOS NUM 
    | NUM 
    ;

tipoOpt: TIPO ID 
       | /* vacío */ 
       ;

/* --- HEURÍSTICAS --- */

declHeuristica: HEURISTICA ID PAR_A ID COMA ID PAR_C LLAVE_A RETORNAR expr PUNTOYCOMA LLAVE_C ;

/* --- REGLAS DE TRÁFICO E ITERACIONES --- */

declRegla: REGLA ID bloque ;

bloque: LLAVE_A instrucciones LLAVE_C ;

instrucciones: instruccion instrucciones 
             | /* vacío */ 
             ;

instruccion: siInstr 
           | paraInstr 
           | asignacion 
           ;

siInstr: SI condicion ENTONCES bloque sinoOpt ;

sinoOpt: SINO bloque 
       | /* vacío */ 
       ;

condicion: HORA_KW ENTRE HORA Y HORA 
         | expr 
         ;

paraInstr: PARA CADA tipoElemento ID DE ID bloque ;

tipoElemento: ARISTA 
            | NODO 
            ;

asignacion: acceso ASIGNA expr PUNTOYCOMA ;

/* --- BÚSQUEDA --- */

busqueda: BUSCAR RUTA ID DESDE ID HASTA ID EN ID USANDO ID conOpt horaOpt PUNTOYCOMA ;

conOpt: CON ID 
      | /* vacío */ 
      ;

horaOpt: A_LAS HORA 
       | /* vacío */ 
       ;

mostrar: MOSTRAR ID PUNTOYCOMA ;

/* --- EXPRESIONES ARITMÉTICAS Y LÓGICAS --- */

expr: expr OPREL suma 
    | suma 
    ;

suma: suma MAS termino
    | suma MENOS termino
    | termino
    ;

termino: termino POR factor
       | termino DIV factor
       | factor
       ;

factor: NUM
      | llamada
      | acceso
      | PAR_A expr PAR_C
      ;

llamada: ID PAR_A argumentos PAR_C ;

argumentos: expr masArgumentos 
          | /* vacío */ 
          ;

masArgumentos: COMA expr masArgumentos 
             | /* vacío */ 
             ;

acceso: ID atributoOpt ;

atributoOpt: PUNTO atributo 
           | /* vacío */ 
           ;

atributo: ID 
        | TIPO 
        ;


/* =========================================================================
   ANALIZADOR LÉXICO (LEXER RULES)
   ========================================================================= */

/* --- PALABRAS RESERVADAS --- */

GRAFO:      'grafo';
DIRIGIDO:   'dirigido';
NODO:       'nodo';
ARISTA:     'arista';
TIPO:       'tipo';

HEURISTICA: 'heuristica';
RETORNAR:   'retornar';
REGLA:      'regla';

SI:         'si';
ENTONCES:   'entonces';
SINO:       'sino';

HORA_KW:    'hora';
ENTRE:      'entre';
Y:          'y';
PARA:       'para';
CADA:       'cada';
DE:         'de';

BUSCAR:     'buscar';
RUTA:       'ruta';
DESDE:      'desde';
HASTA:      'hasta';
EN:         'en';
USANDO:     'usando';
CON:        'con';
MOSTRAR:    'mostrar';

/* --- TOKENS COMPUESTOS --- */

A_LAS:  'a' [ \t]+ 'las';
UNIDAD: 'min' | 'km';

/* --- OPERADORES --- */

OPREL:  '==' | '!=' | '<=' | '>=' | '<' | '>';
MAS:    '+';
MENOS:  '-';
POR:    '*';
DIV:    '/';
FLECHA: '->' | '<->';
ASIGNA: ':=';

/* --- SIGNOS DE PUNTUACIÓN --- */

DOSP:       ':';
PUNTOYCOMA: ';';
COMA:       ',';
PUNTO:      '.';
PAR_A:      '(';
PAR_C:      ')';
LLAVE_A:    '{';
LLAVE_C:    '}';

/* --- LITERALES Y VARIABLES --- */

HORA: [0-9][0-9] ':' [0-9][0-9];
NUM:  [0-9]+ ('.' [0-9]+)?;
ID:   [a-zA-Z_][a-zA-Z_0-9]*;

/* --- IGNORADOS --- */

COMENTARIO: '//' ~[\r\n]* -> skip;
WS:         [ \t\r\n]+ -> skip;
