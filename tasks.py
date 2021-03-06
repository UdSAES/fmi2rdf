#!/usr/bin/env python3
# -*- coding: utf8 -*-

# SPDX-FileCopyrightText: 2022 UdS AES <https://www.uni-saarland.de/lehrstuhl/frey.html>
# SPDX-License-Identifier: MIT


"""CLI for the fmi2rdf-package"""

from invoke import task

from fmi2rdf import assemble_graph, logger


@task(
    help={
        "fmu": "The path to the FMU to be parsed",
        "iri_prefix": "The prefix for generated IRIs, e.g. http://example.com/models",
        "shapes": "Create SHACL shapes graphs? (False if omitted, True otherwise)",
        "format": "The media type for graph serialization",
        "output": "The path of the output file, if desired",
        "filter": "A component name inside an FMU used to identify top-level parameters; can be specified multiple times",
        "blackbox": "Exclude variables that are neither input nor output? (False if omitted, True otherwise)",
    },
    optional=["format", "output", "filter"],
    iterable=["filter"],
)
def fmu2rdf(
    ctx,
    fmu,
    iri_prefix,
    shapes=False,
    blackbox=False,
    filter=None,
    format="text/turtle",
    output=None,
):
    """Create a representation of an FMU in RDF."""

    # Prepare input
    filter_combined = ",".join(filter)

    # Have fmi2rdf build the RDF representation of the given FMU
    graph = assemble_graph(fmu, iri_prefix, shapes, blackbox, filter_combined)

    # Serialize and write to file (or stdout)
    # https://rdflib.readthedocs.io/en/stable/intro_to_parsing.html#saving-rdf
    graph_serialized = graph.serialize(destination=output, format=format)
    if output == None:
        logger.debug(f"Result:\n{graph_serialized}")
    else:
        logger.info(f"Serialized graph to disk as `./{output}`")

    logger.info("Done!")
