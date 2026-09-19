.PHONY: ajuda instalar verificar testes lint tipos banco coletar analisar painel limpar

ajuda:
	@echo "Radar de Fiscalização Municipal"
	@echo ""
	@echo "  make instalar   — cria o ambiente e instala dependências"
	@echo "  make banco      — cria/atualiza o banco local"
	@echo "  make verificar  — lint + tipos + testes (rode antes de dizer 'pronto')"
	@echo "  make coletar    — executa os coletores ativos"
	@echo "  make analisar   — roda as verificações sobre o que foi coletado"
	@echo "  make painel     — sobe o painel local"
	@echo "  make cobertura  — relatório do que o radar NÃO conseguiu ver"

instalar:
	uv venv --python 3.11
	uv pip install -e ".[dev,painel]"

banco:
	python -m radar.cli banco criar

verificar: lint tipos testes

lint:
	ruff check src tests
	ruff format --check src tests

tipos:
	mypy src

testes:
	pytest -m "not rede"

coletar:
	python -m radar.cli coletar --municipio 4105607

analisar:
	python -m radar.cli analisar --municipio 4105607

cobertura:
	python -m radar.cli cobertura --municipio 4105607

painel:
	uvicorn radar.painel.app:app --reload --port 8080

limpar:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
