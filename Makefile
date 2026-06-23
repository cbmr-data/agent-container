# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
.PHONY: container shell sif singularity

# Image name
NAME := agent-container
TAG := $(shell date +"%Y%m%d_0")
# Name of dumps/SIF file
FILENAME := $(NAME)-$(TAG)
# Build directory
BDIR := build
MANAGER := podman

container:
	$(MANAGER) build --build-arg BUILD_TAG=$(TAG) -t $(NAME):latest .

shell: container
	$(MANAGER) run --rm -it --entrypoint /bin/bash $(NAME):latest

sif: singularity

singularity: $(BDIR)/$(FILENAME).sif $(BDIR)/$(NAME)-latest.sif

$(BDIR):
	mkdir -p $@

$(BDIR)/.gitignore: $(BDIR)
	echo "*" > $@

$(BDIR)/$(FILENAME).tar.gz: container $(BDIR) $(BDIR)/.gitignore
	rm -fv "$@"
	$(MANAGER) save localhost/$(NAME):latest --output "${@}"

$(BDIR)/$(FILENAME).sif: $(BDIR)/$(FILENAME).tar.gz
	rm -fv "$@"
	singularity build $(BDIR)/$(FILENAME).sif docker-archive://$(BDIR)/$(FILENAME).tar.gz

$(BDIR)/$(NAME)-latest.sif: $(BDIR)/$(FILENAME).tar.gz
	ln -sf $(FILENAME).sif $(BDIR)/$(NAME)-latest.sif
