# Makefile for xtgen

.PHONY: test install wheel clean demo dev-install help

# Run tests
test:
	@uv run pytest

# Install dependencies
install:
	@uv sync

# Build Wheel
wheel:
	@uv build

# Install with development dependencies
dev-install:
	@uv sync --extra dev

# Clean build artifacts
clean:
	@rm -rf build/ dist/ demo_output/
	@rm -rf .pytest_cache/
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -name "*.pyc" -delete

# Run the main application with default example
demo:
	@mkdir -p build/demo_output
	@uv run xtgen -o build/demo_output

# Show help
help:
	@echo "Available targets:"
	@echo "  test        - Run pytest test suite"
	@echo "  install     - Install dependencies"
	@echo "  dev-install - Install with development dependencies"
	@echo "  demo        - Run xtgen CLI with default counter example to demo_output/"
	@echo "  clean       - Clean build artifacts"
	@echo "  help        - Show this help message"