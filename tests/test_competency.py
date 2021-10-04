#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""Query ontology for answers to competency questions."""

import os

import invoke
import pytest
import rdflib

from fmi2rdf import assemble_graph


class TestCompetency(object):
    def test_sparql_select(self, testcase):
        fmu_path = os.path.abspath(f"./tests/data/{testcase['guid']}.fmu")
        graph = assemble_graph(invoke.context.Context(), fmu_path, False)

        a0 = graph.query(testcase["query"])

        # Construct list of expected literal values
        actual = []
        for row in a0:
            actual.append([item.n3().strip("<>") for item in row])

        # Verify that each expected result is in the list of actual results
        assert [x in actual for x in testcase["expected"]] if actual != [] else False
