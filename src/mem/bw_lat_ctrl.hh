#ifndef __MEM_BW_LAT_CTRL_HH__
#define __MEM_BW_LAT_CTRL_HH__

#include <algorithm>
#include <deque>
#include <filesystem>
#include <fstream>
#include <list>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include "mem/abstract_mem.hh"
#include "mem/port.hh"
#include "mem/simple_mem.hh"
#include "params/BwLatCtrl.hh"

namespace gem5 {

namespace memory {
class BwLatCtrl : public SimpleMemory {

public:
  BwLatCtrl(const BwLatCtrlParams &p);

protected:
  virtual Tick getLatency() const;
  virtual bool recvTimingReq(PacketPtr pkt);
  virtual void dequeue();

private:
  class Curve {
  public:
    using CurvePoint = std::pair<double, double>;

    void push_back(CurvePoint bw_lat_pair) { _curve.push_back(bw_lat_pair); }
    Cycles getClosestMatchingLatency(double bandwidth,
                                     double &latency_overflow_factor) const;
    std::vector<CurvePoint> const curve() { return _curve; };
    void sort();
    const CurvePoint &min() const { return _curve.back(); }
    const CurvePoint &max() const { return _curve.front(); }

  private:
    std::vector<std::pair<double, double>> _curve;
  };
  struct BwLatCtrlStats : public statistics::Group {
    BwLatCtrlStats(BwLatCtrl &ctrl);

    void regStats() override;

    BwLatCtrl &ctrl;
    statistics::Scalar totalDispatchedLatency;
    statistics::Scalar latencyDispatchedCount;

    statistics::Scalar totalRequestedBandwidth;
    statistics::Scalar bandwidthRequestedCount;

    statistics::Scalar totalDispatchedBandwidth;
    statistics::Scalar bandwidthDispatchedCount;
  };

  BwLatCtrlStats stats;

  Tick getClosestMatchingLatency();
  double exponentialIncrement(double, double);

  std::array<Curve, 51> curveMap;
  uint64_t readReqCount{0};
  uint64_t writeReqCount{0};

  const uint32_t samplingWindow;
  Tick currentLatency{20000};
  Tick targetLatency{20000};
  double lastBandwidth{0};
  Cycles systemLatency{250};
  bool didReceiveFirstRequest{false};
  double latencyOverflowFactor = 0.0;

  static constexpr uint16_t TICKS_PER_NS = 1000;
  uint64_t bytesReadCtrl{0};
  uint64_t bytesWrittenCtrl{0};
  Tick lastUpdate{curTick()};
  Tick lastBandwidthReported{curTick()};

  uint32_t dispatchedRequests{0};
};

} // namespace memory
} // namespace gem5
#endif //__MEM_BW_LAT_CTRL_HH__
