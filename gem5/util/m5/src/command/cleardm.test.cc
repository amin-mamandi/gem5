// xalamin

#include <gtest/gtest.h>

#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

uint64_t test_clear_value;

void
test_m5_cleardm(uint64_t clear_value)
{
    test_clear_value = clear_value;
}

DispatchTable dt = { .m5_cleardm = &test_m5_cleardm };

bool
run(std::initializer_list<std::string> arg_args)
{
    Args args(arg_args);
    return Command::run(dt, args);
}

TEST(Cleardm, Arguments)
{
    // Called with no arguments - should fail
    EXPECT_FALSE(run({"cleardm"}));

    // Called with one argument - should succeed
    test_clear_value = 50;
    EXPECT_TRUE(run({"cleardm", "10"}));
    EXPECT_EQ(test_clear_value, 10);

    // Called with two arguments - should fail
    EXPECT_FALSE(run({"cleardm", "10", "20"}));
}