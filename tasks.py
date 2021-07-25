#!/usr/bin/env python3
# -*- coding: utf8 -*-

"""Translation of information about a FMU to RDF"""

import os

from invoke import task
from loguru import logger


@task(
    help={
        "rules": "The full absolute path to the RML rules",
        "serialization": "Serialization format (nquads/turtle/trig/trix/jsonld/hdt)",
        "output": "The path to the output file",
    },
    optional=["serialization", "output"],
)
def rml_modeldescription_xml(ctx, rules, serialization="nquads", output=None):
    """Apply RML rules to `modelDescription.xml`; generate output."""

    mapping = os.path.basename(rules)
    workdir = os.path.dirname(rules)

    prefix = (
        "docker run -i --rm --name rmlmapper "
        f"-v {workdir}:/data "
        "rmlio/rmlmapper-java:latest "
    )

    cmd_container = f"java rmlmapper.jar -m {mapping} -s {serialization}"
    if output != None:
        cmd_container += f" -o {output}"

    cmd = prefix + cmd_container

    logger.debug(cmd)
    ctx.run(cmd)
