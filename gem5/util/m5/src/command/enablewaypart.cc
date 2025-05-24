// xalamin
#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

namespace
{

bool
do_enablewaypart(const DispatchTable &dt, Args &args)
{
    uint64_t enable_value;
    if (!args.pop(enable_value, 0))
        return false;

    printf("Enabled:use waypart = 0x%lx\n", enable_value);
    (*dt.m5_enablewaypart)(enable_value);

    return true;
}

Command enablewaypart = {
    "enablewaypart", 1, 1, do_enablewaypart, "<enable_value>\n"
        "        Enableway partitioin with specified value" };

} // anonymous namespace