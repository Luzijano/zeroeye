.PHONY: install-hooks

install-hooks:
	@echo "Installing pre-commit hook..."
	@if [ ! -d .git ]; then echo "ERROR: Not a git repository."; exit 1; fi
	@mkdir -p .git/hooks
	@ln -sf ../../tools/pre-commit .git/hooks/pre-commit
	@chmod +x tools/pre-commit
	@echo "Pre-commit hook installed successfully."
