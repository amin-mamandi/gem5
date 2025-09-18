import m5

from gem5.modules.options import Options

from gem5.modules.util import fatal_error


def create(options: Options, router_id, latency = 1):
    """
    Create network router
    """

    model  = options.architecture.NOC.network.model
    router = None

    if model == "garnet":
        router = m5.objects.GarnetRouter(
                    router_id = router_id,
                    latency   = latency
                    )
    elif model == "simple":
        router = m5.objects.Switch(
                    router_id = router_id,
                    latency   = latency
                    )
    else:
        fatal_error(f"Unknown network {model}")


    return router
