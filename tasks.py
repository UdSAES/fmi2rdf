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
