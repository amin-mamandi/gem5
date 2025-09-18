from m5.objects.SimpleMemory import SimpleMemory
from m5.params import *
from m5.proxy import *


class BwLatCtrl(SimpleMemory):
    type = "BwLatCtrl"
    cxx_header = "mem/bw_lat_ctrl.hh"
    cxx_class = "gem5::memory::BwLatCtrl"

    curves_path = Param.String(
        "",
        "(absolute) path to the directory containing the Bandwidth Latency Curves",
    )
    sampling_window = Param.Unsigned(
        20000, "Sampling window for access monitoring, in number of accesses"
    )
