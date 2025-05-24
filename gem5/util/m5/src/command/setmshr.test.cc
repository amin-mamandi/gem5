// xalamin

#include <gtest/gtest.h>

#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

uint64_t test_cpu_id;
uint64_t test_mshr_value;

void
test_m5_setmshr(uint64_t cpu_id, uint64_t mshr_value)
{
    test_cpu_id = cpu_id;
    test_mshr_value = mshr_value;
}

DispatchTable dt = { .m5_setmshr = &test_m5_setmshr };

bool
run(std::initializer_list<std::string> arg_args)
{
    Args args(arg_args);
    return Command::run(dt, args);
}

TEST(Setmshr, Arguments)
{
    // Called with no arguments - should fail
    EXPECT_FALSE(run({"setmshr"}));

    // Called with one argument - should fail
    EXPECT_FALSE(run({"setmshr", "10"}));

    // Called with two arguments - should succeed
    test_cpu_id = 50;
    test_mshr_value = 40;
    EXPECT_TRUE(run({"setmshr", "10", "20"}));
    EXPECT_EQ(test_cpu_id, 10);
    EXPECT_EQ(test_mshr_value, 20);

    // Called with three arguments - should fail
    EXPECT_FALSE(run({"setmshr", "10", "20", "30"}));
}