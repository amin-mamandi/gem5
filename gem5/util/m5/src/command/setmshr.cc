// xalamin

#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

namespace
{

bool
do_setmshr(const DispatchTable &dt, Args &args)
{
    uint64_t cpu_id, mshr_value;
    if (!args.pop(cpu_id, 0) || !args.pop(mshr_value, 0))
        return false;

    printf("cpuid = 0x%lx mshr value = 0x%lx\n", cpu_id, mshr_value);
    (*dt.m5_setmshr)(cpu_id, mshr_value);

    return true;
}

Command setmshr = {
    "setmshr", 2, 2, do_setmshr, "<cpu_id> <mshr_value>\n"
        "        Set MSHR value for specified CPU" };

} // anonymous namespace