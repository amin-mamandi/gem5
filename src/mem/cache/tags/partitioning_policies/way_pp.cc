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
        cache(nullptr),
        assoc(params.cache_associativity)

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
                addWayToPartition(alloc_id, way);
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
    }
}

void
WayPartitioningPolicy::addWayToPartition(uint64_t partition_id, unsigned way)
{
    partitionIdWays[partition_id].emplace(way);
}

void
WayPartitioningPolicy::removeWayToPartition(uint64_t partition_id, unsigned way)
{
    partitionIdWays[partition_id].erase(way);
}

void WayPartitioningPolicy::setupNoPartitioning() {
    // Always setup when called, or check if already in no-partitioning mode
    if (partitioningEnabled) {  // Only setup if currently partitioned
        // Clear existing allocations
        partitionIdWays.clear();
        
        // Assign all ways to all possible partition IDs
        for (int partition_id = 0; partition_id < 4; partition_id++) {
            for (unsigned way = 0; way < assoc; way++) {
                addWayToPartition(partition_id, way);
            }
        }
        
        partitioningEnabled = false;
        dmAssoc = false;  // No deterministic filtering for mode 0
        DPRINTF(DetPart, "Mode 0: All partitions assigned all %d ways\n", assoc);
    }
}

void WayPartitioningPolicy::setupPartitioning() {
    // Always setup when called, or check if already partitioned
    if (!partitioningEnabled) {  // Only setup if currently not partitioned
        // Clear existing allocations
        partitionIdWays.clear();

        // Default allocation: each of 4 cores gets a fixed number of ways
        int ways_per_partition = assoc / 4;
        
        for (int partition_id = 0; partition_id < 4; ++partition_id) {
            for (int way = partition_id * ways_per_partition; 
                        way < (partition_id + 1) * ways_per_partition; 
                        ++way) {
                addWayToPartition(partition_id, way);
            }
        }
        
        partitioningEnabled = true;
        dmAssoc = false;  //  Initialize to false, will be set per-request in mode 2
        DPRINTF(DetPart, "Mode 1/2: Default partitioning - %d ways per partition\n", ways_per_partition);
    }
}

void WayPartitioningPolicy::clearDM(uint64_t partition_id, int lowerWay, int upperWay) {
    if (!cache) {
        warn("WayPartitioningPolicy::clearDM called with null cache pointer\n");
        return;
    }

    if (partition_id == 0) {
        auto it = partitionIdWays.find(partition_id);
        if (it != partitionIdWays.end()) {
            int minWay = *std::min_element(it->second.begin(), it->second.end());
            int maxWay = *std::max_element(it->second.begin(), it->second.end());
            
            DPRINTF(DetPart, "Partition 0 has ways: ");
            for (unsigned way : it->second) {
                DPRINTF(DetPart, "%d ", way);
            }
            DPRINTF(DetPart, "\n");
            
            DPRINTF(DetPart, "Clearing DM bits for partition 0 in assigned ways [%d - %d]\n",
                    minWay, maxWay);
            
            cache->clearDeterministicBits(minWay, maxWay);
        } else {
            DPRINTF(DetPart, "No ways assigned to partition 0 for DM clearing\n");
        }
    }
}

void
WayPartitioningPolicy::filterByPartition(
    std::vector<ReplaceableEntry *> &entries,
    const uint64_t partition_id) const
{
    /*
    if (// No entries to filter
        entries.empty() ||
        // This partition_id is not policed
        partitionIdWays.find(partition_id) == partitionIdWays.end()) {
        return;
    } else {
        const auto entries_to_remove = std::remove_if(
            entries.begin(),
            entries.end(),
            [this, partition_id]
            (ReplaceableEntry *entry)
            {
                return partitionIdWays.at(partition_id).find(entry->getWay())
                    == partitionIdWays.at(partition_id).end();
            }
        );

        entries.erase(entries_to_remove, entries.end());
    }
    */
   // If no entries or no ways defined for this partition, return
    if (entries.empty() || partitionIdWays.find(partition_id) == partitionIdWays.end()) {
        DPRINTF(DetPart, "No entries or no ways defined for partition %d\n", partition_id);
        return;
    }

    // DPRINTF(DetPart, "Before way filtering: %d entries for partition %d\n", entries.size(), partition_id);

    // Filter by way allocation
    const auto entries_to_remove = std::remove_if(
        entries.begin(),
        entries.end(),
        [this, partition_id](ReplaceableEntry *entry) {
            return partitionIdWays.at(partition_id).find(entry->getWay())
                == partitionIdWays.at(partition_id).end();
        }
    );
    entries.erase(entries_to_remove, entries.end());

        // DPRINTF(DetPart, "After way filtering: %d entries remain for partition %d\n", entries.size(), partition_id);


    // For mode 2 with dmAssoc, prioritize non-deterministic blocks
    if (dmAssoc && !entries.empty()) {
        bool hasNonDeterministic = std::any_of(entries.begin(), entries.end(),
            [](ReplaceableEntry *entry) { return !entry->isDeterministic(); });
        
        DPRINTF(DetPart, "dmAssoc is enabled, hasNonDeterministic: %d\n", hasNonDeterministic);

        if (hasNonDeterministic) {
            const auto det_entries_to_remove = std::remove_if(
                entries.begin(),
                entries.end(),
                [](ReplaceableEntry *entry) { return entry->isDeterministic(); }
            );
            entries.erase(det_entries_to_remove, entries.end());
        }
    }
    /*
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
    */
}

} // namespace partitioning_policy

} // namespace gem5
