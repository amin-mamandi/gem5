// xalamin

#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

namespace
{

bool
do_cleardm(const DispatchTable &dt, Args &args)
{
    uint64_t clear_value;
    if (!args.pop(clear_value, 0))
        return false;

    printf("Clear DM = 0x%lx\n", clear_value);
    (*dt.m5_cleardm)(clear_value);

    return true;
}

Command cleardm = {
    "cleardm", 1, 1, do_cleardm, "<clear_value>\n"
        "        Clear DM with specified value" };

} // anonymous namespace