// xalamin

#include <gtest/gtest.h>

#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

uint64_t test_enable_value;

void
test_m5_enablememguard(uint64_t enable_value)
{
    test_enable_value = enable_value;
}

DispatchTable dt = { .m5_enablememguard = &test_m5_enablememguard };

bool
run(std::initializer_list<std::string> arg_args)
{
    Args args(arg_args);
    return Command::run(dt, args);
}

TEST(Enablememguard, Arguments)
{
    // Called with no arguments - should fail
    EXPECT_FALSE(run({"enablememguard"}));

    // Called with one argument - should succeed
    test_enable_value = 50;
    EXPECT_TRUE(run({"enablememguard", "10"}));
    EXPECT_EQ(test_enable_value, 10);

    // Called with two arguments - should fail
    EXPECT_FALSE(run({"enablememguard", "10", "20"}));
}