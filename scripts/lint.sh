#!/bin/bash
ruff check src/ tests/
black src/ tests/
