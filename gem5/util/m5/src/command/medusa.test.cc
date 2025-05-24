// xalamin

#include <gtest/gtest.h>

#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

uint64_t test_mask_value;

void
test_m5_medusa(uint64_t mask_value)
{
    test_mask_value = mask_value;
}

DispatchTable dt = { .m5_medusa = &test_m5_medusa };

bool
run(std::initializer_list<std::string> arg_args)
{
    Args args(arg_args);
    return Command::run(dt, args);
}

TEST(medusa, Arguments)
{
    // Called with no arguments - should fail
    EXPECT_FALSE(run({"medusa"}));

    // Called with one argument - should succeed
    test_mask_value = 0;
    EXPECT_TRUE(run({"medusa", "0x3F"}));
    EXPECT_EQ(test_mask_value, 0x3F);

    // Called with two arguments - should fail
    EXPECT_FALSE(run({"medusa", "0x3F", "0x7F"}));
}