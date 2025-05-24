// xalamin
 
#include <gtest/gtest.h>

#include "args.hh"
#include "command.hh"
#include "dispatch_table.hh"

uint64_t test_cpu_id;
uint64_t test_mem_budget;

void
test_m5_setmembudget(uint64_t cpu_id, uint64_t mem_budget)
{
    test_cpu_id = cpu_id;
    test_mem_budget = mem_budget;
}

DispatchTable dt = { .m5_setmembudget = &test_m5_setmembudget };

bool
run(std::initializer_list<std::string> arg_args)
{
    Args args(arg_args);
    return Command::run(dt, args);
}

TEST(Setmembudget, Arguments)
{
    // Called with no arguments - should fail
    EXPECT_FALSE(run({"setmembudget"}));

    // Called with one argument - should fail
    EXPECT_FALSE(run({"setmembudget", "10"}));

    // Called with two arguments - should succeed
    test_cpu_id = 50;
    test_mem_budget = 40;
    EXPECT_TRUE(run({"setmembudget", "10", "20"}));
    EXPECT_EQ(test_cpu_id, 10);
    EXPECT_EQ(test_mem_budget, 20);

    // Called with three arguments - should fail
    EXPECT_FALSE(run({"setmembudget", "10", "20", "30"}));
}