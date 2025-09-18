from gem5.modules.caches.caches import (
    L1D,
    L1I,
    L2,
    IOCache,
    L3Slice,
    WalkCache,
)
from gem5.modules.caches.prefetcher import (
    AMPM,
    BOP,
    DCPT,
    PIF,
    SBOOE,
    IndirectMemory,
    IrregularStreamBuffer,
    SignaturePath,
    SignaturePath2,
    SlimAMPM,
    STeMS,
    Stride,
    Tagged,
)


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
            PIF=PIF,
        ).get(name, None)

    pf_cls = get_prefetcher_class(options.selected)
    return pf_cls(parameters=options.configuration)
