from m5.objects.NDP import NDP
from m5.params import *
from m5.proxy import *


class GemminiDevA(NDP):
    type = "GemminiDevA"
    cxx_header = "gemmini_dev_a/gemmini_dev_a.hh"
    cxx_class = "gem5::GemminiDevA"
