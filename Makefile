# Makefile for xtgen

.PHONY: test install clean dev-install

# Run tests
test:
	uv run pytest

# Install dependencies
install:
	uv sync

# Install with development dependencies
dev-install:
	uv sync --extra dev

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf .pytest_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Run the main application with default example
demo:
	uv run python xtgen.py

# Show help
help:
	@echo "Available targets:"
	@echo "  test        - Run pytest test suite"
	@echo "  install     - Install dependencies"
	@echo "  dev-install - Install with development dependencies"
	@echo "  demo        - Run xtgen with default counter example"
	@echo "  clean       - Clean build artifacts"
	@echo "  help        - Show this help message"