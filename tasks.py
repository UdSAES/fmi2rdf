#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""Translation of information about a FMU to RDF"""

import json
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

    # Identify and parse units defined within the FMU
    units_map = {}
    for unit in md.unitDefinitions:
        logger.debug(f"Parsing unit `{unit.name}`...")

        unit_iri = f"{fmu_iri}/units#{unit.name.replace('/', '_')}"
        unit_uriref = rdflib.URIRef(unit_iri)
        logger.trace(unit_iri)

        units_map[unit.name] = unit_uriref
        graph.add((unit_uriref, RDF.type, FMI.Unit))

    logger.debug(json.dumps(units_map, indent=2))

    # Identify and parse types defined within the FMU
    types_map = {}
    for type in md.typeDefinitions:
        logger.debug(f"Parsing type `{type.name}`...")

        type_iri = f"{fmu_iri}/types#{type.name}"
        type_uriref = rdflib.URIRef(type_iri)
        logger.trace(type_iri)

        types_map[type.name] = type_uriref
        graph.add((type_uriref, RDF.type, FMI.SimpleType))

        graph = add_variable_constraints(graph, units_map, type_uriref, type)

    logger.debug(json.dumps(types_map, indent=2))

    # Identify and parse variables defined within the FMU
    for var in md.modelVariables:
        logger.debug(f"Parsing variable `{var.name}`...")

        var_iri = f"{fmu_iri}/variables#{var.name}"
        var_uriref = rdflib.URIRef(var_iri)
        logger.trace(var_iri)

        # Distinguish between parameters, inputs, outputs, and internal variables
        if var.causality in ["parameter", "calculatedParameter", "input", "output"]:
            if var.causality == "parameter" or var.causality == "calculatedParameter":
                if blackbox == True:
                    # Only parse top-level parameters
                    # XXX Assumes hierarchical component names!
                    if not ("." in var.name):
                        graph.add((var_uriref, RDF.type, FMI.Parameter))
                        graph.add((fmu_uriref, FMI.hasParameter, var_uriref))
                    else:
                        continue
                else:
                    graph.add((var_uriref, RDF.type, FMI.Parameter))
                    graph.add((fmu_uriref, FMI.hasParameter, var_uriref))
            if var.causality == "input":
                graph.add((var_uriref, RDF.type, FMI.Input))
                graph.add((fmu_uriref, FMI.hasInput, var_uriref))
            if var.causality == "output":
                graph.add((var_uriref, RDF.type, FMI.Output))
                graph.add((fmu_uriref, FMI.hasOutput, var_uriref))

            graph.add((var_uriref, RDF.type, FMI.ScalarVariable))

            if var.description != None:
                graph.add(
                    (var_uriref, DCT.description, rdflib.Literal(var.description))
                )
            if var.start != None:
                graph.add((var_uriref, FMI.start, rdflib.Literal(var.start)))

            graph = add_variable_constraints(graph, units_map, var_uriref, var)

            if var.declaredType != None:
                try:
                    graph.add(
                        (var_uriref, FMI.declaredType, types_map[var.declaredType.name])
                    )
                    graph = add_variable_constraints(
                        graph, units_map, var_uriref, var.declaredType
                    )
                except KeyError:
                    logger.warning(
                        f"Type `{var.declaredType.name}` for variable `{var.name}` not found!"
                    )
                    continue

    # Serialize graph and write to disk
    output = "local/output.ttl"
    logger.info(f"Serializing graph to disk as `./{output}`...")
    graph.serialize(destination=output, format="ttl")


def add_variable_constraints(graph, units_map, uriref, object):
    try:
        graph.add((uriref, FMI.unit, units_map[object.unit]))
    except KeyError:
        logger.warning(f"Unit `{object.unit}` for object `{object.name}` not found!")

    if object.min != None:
        graph.add((uriref, FMI.min, rdflib.Literal(object.min)))
        # graph.add((uriref, QUDT.minInclusive, rdflib.Literal(object.min)))
    if object.max != None:
        graph.add((uriref, FMI.max, rdflib.Literal(object.max)))
        # graph.add((uriref, QUDT.maxInclusive, rdflib.Literal(object.max)))
    if object.nominal != None:
        graph.add((uriref, FMI.nominal, rdflib.Literal(object.nominal)))

    return graph
