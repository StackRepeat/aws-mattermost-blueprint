.PHONY: manifest fmt init validate shellcheck test

TERRAFORM ?= terraform
PYTHON ?= python3

manifest:
	$(PYTHON) scripts/validate_blueprint.py

fmt:
	$(TERRAFORM) -chdir=terraform fmt -check -recursive

init:
	$(TERRAFORM) -chdir=terraform init -backend=false -input=false

validate:
	$(TERRAFORM) -chdir=terraform validate -no-color

shellcheck:
	find api_helpers -type f -name '*.sh' -exec bash -n {} +

test: manifest fmt init validate shellcheck
