.PHONY: manifest fmt init validate shellcheck unit plan-test smoke-docker test

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
	find api_helpers -type f -name '*.sh' -exec bash -n {} \;
	bash -n terraform/templates/bootstrap.sh.tftpl

unit:
	$(PYTHON) -m unittest discover -s tests -v

plan-test:
	$(TERRAFORM) -chdir=terraform test -no-color

smoke-docker:
	$(PYTHON) scripts/smoke-local.py

test: manifest fmt init validate shellcheck unit plan-test
