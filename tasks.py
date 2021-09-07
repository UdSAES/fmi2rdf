#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""Translation of information about a FMU to RDF"""

import os

import fmpy
import rdflib
from invoke import task
from loguru import logger
from rdflib.namespace import OWL, RDF, XSD

# Declare namespaces to enable enforcing consistent prefixes
DCT = rdflib.Namespace("http://purl.org/dc/terms/")
QUDT = rdflib.Namespace("http://qudt.org/schema/qudt/")
UNIT = rdflib.Namespace("http://qudt.org/vocab/unit/")
FMI = rdflib.Namespace("https://ontologies.msaas.me/fmi-ontology.ttl#")
SMS = rdflib.Namespace("https://ontologies.msaas.me/sms-ontology.ttl#")
ABOX = rdflib.Namespace("https://abox.msaas.me/")


@task(
    help={
        "rules": "The full absolute path to the RML rules",
        "serialization": "Serialization format (nquads/turtle/trig/trix/jsonld/hdt)",
        "output": "The path to the output file",
    },
    optional=["serialization", "output"],
)
def apply_rml(ctx, rules, serialization="nquads", output=None):
    """
    Apply RML rules; generate output.

    The target file on which the rules are applied is defined in the rules!
    """
    logger.debug(f"Applying RML mappings defined in '{os.path.basename(rules)}'...")

    mapping = os.path.basename(rules)
    workdir = os.path.dirname(rules)

    prefix = (
        "podman run -i --rm --name rmlmapper "
        f"-v {workdir}:/data:Z "
        "rmlio/rmlmapper-java:latest "
    )

    cmd_container = f"java rmlmapper.jar -m {mapping} -s {serialization}"
    if output != None:
        cmd_container += f" -o {output}"

    cmd = prefix + cmd_container

    logger.trace(cmd)
    result = ctx.run(cmd, hide="out")

    if result.ok:
        logger.debug(f"\n{result.stdout}")
        return result.stdout
    else:
        logger.warning(result)


@task(
    help={
        "fmu_path": "The full path to the FMU to be parsed",
        "blackbox": "Whether or not to include variables that are neither input nor ouptut",
    },
    optional=["blackbox"],
)
def assemble_graph(ctx, fmu_path, blackbox=False):
    """Collect information about a FMU as a RDF graph."""

    logger.info(f"Parsing FMU {os.path.basename(fmu_path)}...")

    # Read model description using FMPy
    try:
        md = fmpy.read_model_description(fmu_path)
    except fmpy.ValidationError as e:
        logger.error(e)

    # Create empty graph and define prefixes to be used
    graph = rdflib.Graph()

    graph.bind("dct", DCT, override=True, replace=True)
    graph.bind("qudt", QUDT, override=True, replace=True)

    graph.bind("fmi", FMI, override=True, replace=True)

    # Parse basic metadata about FMU to RDF
    iri_prefix = os.getenv("FMI2RDF_IRI_PREFIX", "http://example.org/FMUs")
    fmu_iri = f"{iri_prefix}/{md.guid.strip('{}')}"
    fmu_uriref = rdflib.URIRef(fmu_iri)

    graph.add((fmu_uriref, RDF.type, FMI.FMU))

    mappings = [
        (FMI.fmiVersion, md.fmiVersion, XSD.normalizedString),
        (FMI.modelName, md.modelName, XSD.string),
        (FMI.guid, md.guid.strip("{}"), XSD.normalizedString),
        (FMI.generationTool, md.generationTool, XSD.normalizedString),
        (FMI.generationDateAndTime, md.generationDateAndTime, XSD.dateTime),
        (
            FMI.variableNamingConvention,
            md.variableNamingConvention,
            XSD.normalizedString,
        ),
        (FMI.numberOfEventIndicators, md.numberOfEventIndicators, XSD.unsignedInt),
    ]  # literals only!

    for p, o, d in mappings:
        graph.add((fmu_uriref, p, rdflib.Literal(o, datatype=d)))

    # Serialize graph and write to disk
    output = "local/output.ttl"
    logger.info(f"Serializing graph to disk as `./{output}`...")
    graph.serialize(destination=output, format="ttl")
