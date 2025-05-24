/*
 * Copyright (c) 2024 ARM Limited
 * All rights reserved.
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "mem/cache/tags/partitioning_policies/way_pp.hh"

#include <algorithm>

#include "base/logging.hh"
#include "base/trace.hh"
#include "params/WayPartitioningPolicy.hh"
#include "way_allocation.hh"
#include "sim/system.hh"

namespace gem5
{

namespace partitioning_policy
{

WayPartitioningPolicy::WayPartitioningPolicy
    (const WayPartitioningPolicyParams &params): 
        BasePartitioningPolicy(params),
        assoc(params.cache_associativity),
        cache(nullptr)
{
    // get cache associativity and check it is usable for this policy
    const auto cache_assoc = assoc;
    assert(cache_assoc > 0);

    // iterate over all provided allocations
    for (const auto allocation: params.allocations) {
        const auto alloc_id = allocation->getPartitionId();

        // save way allocations in policy
        for (const auto way: allocation->getWays()) {

            // check if allocations are valid
            fatal_if(way >= cache_assoc, "Way Partitioning Policy allocation "
                "for PartitionID: %d, Way: %d cannot be fullfiled as cache "
                "associativity is %d", alloc_id, way, cache_assoc);

            if (this->partitionIdWays[alloc_id].count(way) == 0) {
                this->partitionIdWays[alloc_id].emplace(way);
            } else {
                // do not add duplicate allocation to policy and warn
                warn("Duplicate Way Partitioning Policy allocation for "
                    "PartitionID: %d, Way: %d",
                    alloc_id, way);
            }
        }

        // report allocation of policies
        DPRINTF(DetPart, "Allocated %d ways in WayPartitioningPolicy "
            "for PartitionID: %d \n", allocation->getWays().size(),
            alloc_id);
        DPRINTF(DetPart, "is partitioningEnabled=%d\n", partitioningEnabled);
    }
}

void
WayPartitioningPolicy::setWayAllocation(uint64_t partition_id, int lowerNum, int upperNum)
{            
    // Validate ranges
    fatal_if(lowerNum < 0, "Lower allocation limit must be >= 0");
    fatal_if(upperNum < 0, "Upper allocation limit must be >= 0");
    fatal_if(upperNum >= assoc, "Upper allocation limit must be less than the associativity");

    // Clear old allocation
    partitionIdWays[partition_id].clear();

    // Set new allocation
    DPRINTF(PartitionPolicy, "Setting new allocation for partition ID %d\n", partition_id);
    for (int way = lowerNum; way <= upperNum; way++) {
        partitionIdWays[partition_id].emplace(way);
    }
}

void
WayPartitioningPolicy::clearDM(uint64_t partition_id, int lowerWay, int upperWay)
{
    if (!cache) {
        warn("WayPartitioningPolicy::clearDM called with null cache pointer\n");
        return;
    }

    DPRINTF(DetPart, "Clearing DM bits for PartitionID %d in ways [%d - %d]\n",
            partition_id, lowerWay, upperWay);

    // Delegate to BaseTags to clear deterministic bits in specified way range
    cache->clearDeterministicBits(lowerWay, upperWay);
}

void
WayPartitioningPolicy::filterByPartition(
    std::vector<ReplaceableEntry *> &entries,
    const uint64_t partition_id) const
{

        // Skip filtering if partitioning is disabled
    if (!partitioningEnabled) {
        DPRINTF(PartitionPolicy, "Partitioning is disabled, allowing all %d entries\n", entries.size());
        return;
    }

    DPRINTF(PartitionPolicy, "Before filtering: %d entries for partition %d, dmAssoc=%d\n", 
           entries.size(), partition_id, dmAssoc);
    
    // Print entry ways before filtering
    if (entries.size() > 0) {
        std::string ways = "";
        for (const auto& entry : entries) {
            ways += csprintf("%d(det=%d) ", entry->getWay(), entry->isDeterministic());
        }
        DPRINTF(DetPart, "Entry ways before filtering: %s\n", ways);
    }

    // If no entries to filter or partition_id not policed, return
    if (entries.empty() || partitionIdWays.find(partition_id) == partitionIdWays.end()) {
        DPRINTF(DetPart, "No entries or no ways defined for partition %d\n", partition_id);
        return;
    }

    // First, filter by way allocation
    auto entries_it = std::remove_if(
        entries.begin(),
        entries.end(),
        [this, partition_id](ReplaceableEntry *entry)
        {
            bool keep = partitionIdWays.at(partition_id).find(entry->getWay())
                != partitionIdWays.at(partition_id).end();
            DPRINTF(PartitionPolicy, "Way %d for partition %d: %s\n", 
                   entry->getWay(), partition_id, keep ? "keep" : "remove");
            return !keep;
        }
    );
    entries.erase(entries_it, entries.end());

    // Show results after filtering
    DPRINTF(PartitionPolicy, "After way filtering: %d entries remain\n", entries.size());
    
    // Now, if in deterministic mode (mode 2), prioritize non-deterministic blocks
    if (dmAssoc && !entries.empty()) {
        // Check if there are any non-deterministic entries
        bool hasNonDeterministic = false;
        for (const auto entry : entries) {
            if (!entry->isDeterministic()) {
                hasNonDeterministic = true;
                break;
            }
        }

        DPRINTF(PartitionPolicy, "dmAssoc=true, hasNonDeterministic=%d\n", hasNonDeterministic);
        
        // If we have non-deterministic entries, filter out deterministic ones
        if (hasNonDeterministic) {
            entries_it = std::remove_if(
                entries.begin(),
                entries.end(),
                [this](ReplaceableEntry *entry)  // Add 'this' to the capture list
                {
                    DPRINTF(PartitionPolicy, "Checking entry way=%d, isDet=%d\n", 
                        entry->getWay(), entry->isDeterministic());
                    return entry->isDeterministic();
                }
            );
            entries.erase(entries_it, entries.end());
            
            DPRINTF(PartitionPolicy, "After deterministic filtering: %d entries remain\n", entries.size());
        }
    }

    // Print final selected entries
    if (entries.size() > 0) {
        std::string finalWays = "";
        for (const auto& entry : entries) {
            finalWays += csprintf("%d(det=%d) ", entry->getWay(), entry->isDeterministic());
        }
        DPRINTF(PartitionPolicy, "Final entries after all filtering: %s\n", finalWays);
    }
}

} // namespace partitioning_policy

} // namespace gem5
