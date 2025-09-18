
from gem5.modules.caches.caches import IOCache
from gem5.modules.caches.caches import L1I, L1D, WalkCache, L2, L3Slice

from gem5.modules.caches.prefetcher import Stride
from gem5.modules.caches.prefetcher import Tagged
from gem5.modules.caches.prefetcher import IndirectMemory
from gem5.modules.caches.prefetcher import SignaturePath
from gem5.modules.caches.prefetcher import SignaturePath2
from gem5.modules.caches.prefetcher import AMPM
from gem5.modules.caches.prefetcher import DCPT
from gem5.modules.caches.prefetcher import IrregularStreamBuffer
from gem5.modules.caches.prefetcher import SlimAMPM
from gem5.modules.caches.prefetcher import BOP
from gem5.modules.caches.prefetcher import SBOOE
from gem5.modules.caches.prefetcher import STeMS
from gem5.modules.caches.prefetcher import PIF


def get_prefetcher(options):
    def get_prefetcher_class(name: str):
        return dict(
            Stride=Stride,
            Tagged=Tagged,
            IndirectMemory=IndirectMemory,
            SignaturePath=SignaturePath,
            SignaturePath2=SignaturePath2,
            AMPM=AMPM,
            DCPT=DCPT,
            IrregularStreamBuffer=IrregularStreamBuffer,
            SlimAMPM=SlimAMPM,
            BOP=BOP,
            SBOOE=SBOOE,
            STeMS=STeMS,
            PIF=PIF
        ).get(name, None)
    pf_cls = get_prefetcher_class(options.selected)
    return pf_cls(parameters=options.configuration)
