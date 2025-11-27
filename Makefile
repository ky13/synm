up:
	@docker compose up -d
down:
	@docker compose down
logs:
	@docker compose logs -f
seed:
	@python -m scripts.seed
test:
	@pytest -q
fmt:
	@ruff check --fix .
	@black .