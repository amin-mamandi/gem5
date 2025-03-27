/*
 * Copyright (c) 2024 Arm Limited
 * All rights reserved
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

#ifndef __MEM_CACHE_TAGS_PARTITIONING_MANAGER_HH__
#define __MEM_CACHE_TAGS_PARTITIONING_MANAGER_HH__

#include "mem/packet.hh"
#include "params/PartitionManager.hh"
#include "sim/sim_object.hh"
#include "debug/PartitioningPolicies.hh"

namespace gem5
{

class ReplaceableEntry;

namespace partitioning_policy
{

class BasePartitioningPolicy;

class PartitionManager : public SimObject
{
  public:
    PARAMS(PartitionManager);
    PartitionManager(const Params &p);

    /**
    * PartitionManager interface to retrieve PartitionID from a packet;
    * This base implementation returns zero by default.
    *
    * @param pkt pointer to packet (PacketPtr)
    * @return packet PartitionID.
    */
    virtual uint64_t
    readPacketPartitionID(PacketPtr pkt) const
    {
      // Try to determine which CPU the request is from based on requestorID
      RequestorID req_id = pkt->req->requestorId();
      
      // RequestorIDs are typically assigned in a pattern where:
      // CPU 0: data=8, inst=7, dtb_walker=3, itb_walker=4, etc.
      // CPU 1: data=14, inst=13, dtb_walker=9, itb_walker=10, etc.
      // CPU 2: data=20, inst=19, dtb_walker=15, itb_walker=16, etc.
      // CPU 3: data=26, inst=25, dtb_walker=21, itb_walker=22, etc.
      
      // Map requestor ID to CPU ID (these mappings need to be adjusted for your system)
      int cpu_id = -1;
      
      if (req_id >= 3 && req_id <= 8) {
          cpu_id = 0;  // CPU 0 requestors
      } else if (req_id >= 9 && req_id <= 14) {
          cpu_id = 1;  // CPU 1 requestors  
      } else if (req_id >= 15 && req_id <= 20) {
          cpu_id = 2;  // CPU 2 requestors
      } else if (req_id >= 21 && req_id <= 26) {
          cpu_id = 3;  // CPU 3 requestors
      }
      
      DPRINTF(PartitioningPolicies, "Packet from requestor %d assigned to partition ID %d\n", 
              req_id, (cpu_id == 0) ? 0 : 1);
      
      // Map CPU 0 to partition ID 0, all others to partition ID 1
      return (cpu_id == 0) ? 0 : 1;

      // return 0;
    };

    /**
    * Notify of acquisition of ownership of a cache line
    * @param partition_id PartitionID of the upstream memory request
    */
    void notifyAcquire(uint64_t partition_id);

    void notifyRelease(uint64_t partition_id);

    void filterByPartition(std::vector<ReplaceableEntry *> &entries,
        const uint64_t partition_id) const;

  protected:
    /** Partitioning policies */
    std::vector<partitioning_policy::BasePartitioningPolicy *>
        partitioningPolicies;
};

} // namespace partitioning_policy

} // namespace gem5

#endif // __MEM_CACHE_TAGS_PARTITIONING_MANAGER_HH__
