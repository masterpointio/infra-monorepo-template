#!/usr/bin/env python3
"""Compatibility entry point for the six child tests and any added cases."""

from module_checks import check_results, run_process  # Public checker compatibility.
from test_examples import entrypoint

if __name__ == "__main__":
    entrypoint(default_module="child-modules/random-pet")
