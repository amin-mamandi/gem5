//xalamin
#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

namespace
{

bool
do_setmembudget(const DispatchTable &dt, Args &args)
{
    uint64_t cpu_id, mem_budget;
    if (!args.pop(cpu_id, 0) || !args.pop(mem_budget, 0))
        return false;

    (*dt.m5_setmembudget)(cpu_id, mem_budget);

    return true;
}

Command setmembudget = {
    "setmembudget", 2, 2, do_setmembudget, "<cpu_id> <mem_budget>\n"
        "        Set memory budget for specified CPU" };

} // anonymous namespace