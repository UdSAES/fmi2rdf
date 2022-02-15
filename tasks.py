#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""CLI for the fmi2rdf-package"""

from invoke import task

from fmi2rdf import assemble_graph, logger


@task(
    help={
        "fmu": "The path to the FMU to be parsed",
        "iri_prefix": "The prefix for generated IRIs, e.g. http://example.com/models",
        "shapes": "Whether or not to generate SHACL shapes graphs (default: False)",
        "format": "The media type for graph serialization",
        "output": "The path of the output file, if desired",
        "filter": "A component name inside an FMU used to identify top-level parameters; can be specified multiple times",
        "blackbox": "Whether or not to include variables that are neither input nor output (default: False)",
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
