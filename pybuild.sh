#!/bin/bash

COMMIT_HASH=$(git rev-parse --short=8 HEAD)
sed -i "s/^COMMIT_HASH = .*/COMMIT_HASH = \"$COMMIT_HASH\"/" src/emd/revision.py
poetry build
