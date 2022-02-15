#!/usr/bin/env python3
# -*- coding: utf8 -*-

# SPDX-FileCopyrightText: 2022 UdS AES <https://www.uni-saarland.de/lehrstuhl/frey.html>
# SPDX-License-Identifier: MIT


"""Query ontology for answers to competency questions."""

import os

import invoke
import pytest
import rdflib

from fmi2rdf import assemble_graph


class TestCompetency(object):
    def test_sparql_select(self, testcase, monkeypatch):
        # Select exemplary FMU
        fmu_path = os.path.abspath(f"./tests/data/{testcase['guid']}.fmu")
        iri_prefix = "http://example.org/FMUs"

        # Build graph; executy query from test case
        graph = assemble_graph(fmu_path, iri_prefix)

        a0 = graph.query(testcase["query"])

        # Construct list of expected literal values
        actual = []
        for row in a0:
            actual.append([item.n3().strip("<>") for item in row])

        # Verify that each expected result is in the list of actual results
        assert testcase["expected"] == actual
