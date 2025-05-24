// xalamin
#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

namespace
{

bool
do_medusa(const DispatchTable &dt, Args &args)
{
    uint64_t mask_value;
    if (!args.pop(mask_value, 0))
        return false;

    printf("Setting: medusa reserved bank mask = 0x%lx\n", mask_value);
    (*dt.m5_medusa)(mask_value);

    return true;
}

Command medusa = {
    "medusa", 1, 1, do_medusa, "<mask_value>\n"
        "        Set Medusa reserved bank mask with specified value" };

} // anonymous namespace