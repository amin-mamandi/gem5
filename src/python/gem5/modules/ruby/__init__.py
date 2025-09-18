import importlib

import m5

from gem5.modules.ruby.memory import configure_mem_region_controller


def configure_ruby(system, options, piobus=None, dma_ports=[], bootmem=None):
    protocol_name = m5.defines.buildEnv["PROTOCOL"]

    protocol = importlib.import_module(
        f"gem5.modules.ruby.protocol.{protocol_name}"
    )

    protocol.configure_ruby(system, options, piobus, dma_ports, bootmem)
