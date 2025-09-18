import m5
import os, sys

from gem5.modules.system import System
from gem5.modules.options import Options
from gem5.modules.simulation import Simulation


options = Options()

if options.disable_listeners:
    print("Disabling Listeners")
    m5.disableAllListeners()

init_system = System(options)

root = m5.objects.Root(system=init_system, full_system=options.simulation.fs_mode) 

if options.simulation.fs_mode:
    if options.simulation.timesync:
        root.time_sync_enable = True

    if not options.bare_metal and not options.dtb_filename:
        if options.architecture.system.model not in [
                                    "VExpress_GEM5",
                                    "VExpress_GEM5_V1",
                                    "VExpress_GEM5_V2",
                                    "VExpress_GEM5_Foundation"]:
            print("Can only correctly generate a dtb for VExpress_GEM5")
            sys.exit(1)
        root.system.workload.dtb_filename = os.path.join(m5.options.outdir, '%s.dtb' % "system")
        root.system.generateDtb(root.system.workload.dtb_filename)


Simulation(root, init_system, options)

sys.exit(0)
