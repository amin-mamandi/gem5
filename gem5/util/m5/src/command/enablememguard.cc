// xalamin
#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

namespace
{

bool
do_enablememguard(const DispatchTable &dt, Args &args)
{
    uint64_t enable_value;
    if (!args.pop(enable_value, 0))
        return false;

    printf("Enabled:use memguard = 0x%lx\n", enable_value);
    (*dt.m5_enablememguard)(enable_value);

    return true;
}

Command enablememguard = {
    "enablememguard", 1, 1, do_enablememguard, "<enable_value>\n"
        "        Enable memory guard with specified value" };

} // anonymous namespace