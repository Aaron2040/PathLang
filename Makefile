# Makefile para PathLang
# Uso en Linux/WSL:
#   make generate       -> compila la gramática con ANTLR4 hacia la carpeta gen/
#   make test-lexer     -> muestra tokens para todos los tests
#   make test-valid     -> análisis completo de tests válidos
#   make test-errors    -> análisis completo de tests de error
#   make test-all       -> corre todos los tests completos
#   make clean          -> limpia archivos generados

ANTLR_JAR   = antlr-4.13.1-complete.jar
PYTHON      = python3
TEST_DIR    = tests
GEN_DIR     = gen

generate:
	java -jar $(ANTLR_JAR) -Dlanguage=Python3 -visitor -o $(GEN_DIR) PathLang.g4
	@echo "Archivos Python generados correctamente en la carpeta $(GEN_DIR)."

test-valid: generate
	@echo "\n===== TESTS VÁLIDOS ====="
	@for f in $(TEST_DIR)/validos/test_valido_*.txt; do \
		echo "\n--- $$f ---"; \
		PYTHONPATH=$(GEN_DIR) $(PYTHON) main.py $$f; \
	done

test-errors: generate
	@echo "\n===== TESTS DE ERROR ====="
	@for f in $(TEST_DIR)/errores/*/*.txt; do \
		echo "\n--- $$f ---"; \
		PYTHONPATH=$(GEN_DIR) $(PYTHON) main.py $$f; \
	done

test-all: test-valid test-errors

test-lexer: generate
	@echo "\n===== ANÁLISIS LÉXICO (tokens) ====="
	PYTHONPATH=$(GEN_DIR) $(PYTHON) lexer_test.py


clean:
	rm -rf $(GEN_DIR)
	rm -rf __pycache__
