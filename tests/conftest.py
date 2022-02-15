#!/usr/bin/env python3
# -*- coding: utf8 -*-

# SPDX-FileCopyrightText: 2022 UdS AES <https://www.uni-saarland.de/lehrstuhl/frey.html>
# SPDX-License-Identifier: MIT


"""Provide global test fixtures for unit tests."""

import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import fmi2rdf  # noqa -- import has to happen _after_ modifying PATH


def pytest_generate_tests(metafunc):

    # Load questions from file
    with open("tests/questions.yaml", "r") as fp:
        collection = yaml.full_load(fp)

    if "testcase" in metafunc.fixturenames:
        metafunc.parametrize("testcase", collection["testcases"])
