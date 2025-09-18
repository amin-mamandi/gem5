#include "mem/bw_lat_ctrl.hh"
#include "base/logging.hh"
#include "base/trace.hh"
#include "debug/BwLatCtrl.hh"
#include "mem/packet.hh"
#include "sim/cur_tick.hh"

namespace gem5 {
namespace memory {
BwLatCtrl::BwLatCtrl(const BwLatCtrlParams &p)
    : SimpleMemory(p), stats(*this), samplingWindow(p.sampling_window) {

  // Very bad hack to get the ratio between reads and writes
  // from the filename
  auto get_rw_ratio = [](std::string path) {
    std::string base_filename = path.substr(path.find_last_of("/\\") + 1);
    std::string noext =
        base_filename.substr(0, base_filename.find_last_of("."));
    std::string rw_ratio_str = noext.substr(noext.find_last_of("bwlat_") + 1);
    unsigned n_rw_ratio = std::atoll(rw_ratio_str.c_str());
    return n_rw_ratio;
  };

  // Read from the directory containing the path of the curves
  DPRINTF(BwLatCtrl, "Getting curves from %s\n", p.curves_path);

  for (const auto &curve_path :
       std::filesystem::directory_iterator(p.curves_path)) {
    DPRINTF(BwLatCtrl, "Reading file: %s\n", curve_path);
    std::ifstream curve_file(curve_path.path());

    Curve curve;
    double tmp_lat;
    double tmp_bw;

    while (curve_file >> tmp_bw >> tmp_lat) {
      curve.push_back(std::make_pair(tmp_lat, tmp_bw));
    }

    auto rw_ratio = get_rw_ratio(curve_path.path());
    panic_if(rw_ratio % 2 != 0, "rw_ratio must be even");
    curve.sort();
    curveMap[rw_ratio >> 1] = curve;
  }
  DPRINTF(BwLatCtrl, "Read %d curves from %s\n", curveMap.size(),
          p.curves_path);
}

Tick BwLatCtrl::getLatency() const { return currentLatency; }

bool BwLatCtrl::recvTimingReq(PacketPtr pkt) {

  DPRINTF(BwLatCtrl, "recvTimingReq: request %s addr %#x size %d\n",
          pkt->cmdString(), pkt->getAddr(), pkt->getSize());

  pkt->headerDelay = 0;
  pkt->payloadDelay = 0;
  if (!didReceiveFirstRequest) {
    lastUpdate = curTick();
    didReceiveFirstRequest = true;
  }

  readReqCount += pkt->isRead();
  writeReqCount += pkt->isWrite();
  bytesReadCtrl += (pkt->isRead() * pkt->getSize());
  bytesWrittenCtrl += (pkt->isWrite() * pkt->getSize());

  // Every samplingWindow requests, update latency
  if (((readReqCount + writeReqCount) % samplingWindow) == 0) {
    targetLatency =
        Tick(double(getClosestMatchingLatency()) * (1 + latencyOverflowFactor));

    // Increment in 5% amts
    auto increment_amt = exponentialIncrement(currentLatency, targetLatency);
    auto next_latency = Tick(double(currentLatency) + increment_amt);
    DPRINTF(BwLatCtrl,
            "Modifying latency: cur = %lld, next = %lld, target = %lld\n",
            currentLatency, next_latency, targetLatency);
    currentLatency = next_latency;

    bytesReadCtrl = 0;
    bytesWrittenCtrl = 0;
    lastUpdate = curTick();
  }

  return SimpleMemory::recvTimingReq(pkt);
}

void BwLatCtrl::dequeue() {

  stats.totalRequestedBandwidth += lastBandwidth;
  stats.bandwidthRequestedCount += 1;
  stats.totalDispatchedLatency += ticksToCycles(currentLatency);
  stats.latencyDispatchedCount += 1;

  SimpleMemory::dequeue();
}

Tick BwLatCtrl::getClosestMatchingLatency() {

  uint8_t rw_ratio =
      std::ceil((float)readReqCount / (readReqCount + writeReqCount) * 100);

  // round (up) to nearest multiple of 2
  rw_ratio = (rw_ratio >> 1) << 1;

  double bytes_rw = bytesReadCtrl + bytesWrittenCtrl;
  double bandwidth_mb =
      bytes_rw / (double(curTick() - lastUpdate) / TICKS_PER_NS) * 1000;
  DPRINTF(BwLatCtrl, "RW Ratio is %d: got %d reads and %d writes\n", rw_ratio,
          readReqCount, writeReqCount);
  DPRINTF(BwLatCtrl, "Estimated BW is %.4f MB/s\n", bandwidth_mb);

  lastBandwidth = bandwidth_mb;

  // got 51 curves -> store them as their rw_ratio / 2
  const auto &curve = curveMap[rw_ratio >> 1];
  // getClosestMatchingLatency returns lat in cycles
  // I need it in ticks
  auto scaled_latency =
      curve.getClosestMatchingLatency(bandwidth_mb, latencyOverflowFactor);

  if (systemLatency >= scaled_latency) {
    DPRINTF(BwLatCtrl, "Got minimum latency, returning 0\n");
    return 0;
  }

  return cyclesToTicks(scaled_latency - systemLatency);
}

double BwLatCtrl::exponentialIncrement(double current_latency,
                                       double target_latency) {
  const double EXPONENTIAL_INCREMENT_FACTOR = 20.0;

  return (target_latency - current_latency) / EXPONENTIAL_INCREMENT_FACTOR;
}

// Curve Object

void BwLatCtrl::Curve::sort() {
  push_back(std::make_pair(0, 0));
  std::sort(_curve.begin(), _curve.end(),
            [](const auto &cur_pair, const auto &other_pair) {
              return cur_pair.second > other_pair.second;
            });
}

Cycles BwLatCtrl::Curve::getClosestMatchingLatency(
    double bandwidth, double &latency_overflow_factor) const {
  const auto &name = []() { return "::Curve"; };

  // Check if I'm over the range or under
  auto highest_bw = _curve.front().second;
  auto lowest_bw = _curve.back().second;
  auto highest_lat = _curve.front().first;
  auto lowest_lat = _curve.back().first;

  // Boundary conditions:
  // I'm outside the curve
  if (bandwidth >= highest_bw) {
    latency_overflow_factor += 0.02;
    DPRINTF(BwLatCtrl,
            "Bandwidth over the limit: responding with (max) lat = %lld\n",
            highest_lat);
    return Cycles(highest_lat);
  }

  if (bandwidth <= lowest_bw) {
    DPRINTF(BwLatCtrl,
            "Bandwidth below the limit: responding with (min) lat = %lld\n",
            lowest_lat);
    return Cycles(lowest_lat);
  }

  // Main:
  // Look for a point within the curve,
  // interpolate using the current and next bandwidth value
  const auto &lower_bound_it = std::lower_bound(
      _curve.begin(), _curve.end(), bandwidth,
      [](const std::pair<double, double> &cur_pair, const double &bandwidth) {
        return cur_pair.second > bandwidth;
      });

  const auto lower_bound_lat = lower_bound_it->first;
  const auto lower_bound_bw = lower_bound_it->second;

  const auto &upper_bound_it = std::prev(lower_bound_it);
  const auto upper_bound_lat = upper_bound_it->first;
  const auto upper_bound_bw = upper_bound_it->second;

  const auto slope =
      (bandwidth - lower_bound_bw) / (upper_bound_bw - lower_bound_bw);
  const auto latency_increase_from_base =
      (upper_bound_lat - lower_bound_lat) * slope;
  auto latency_value = lower_bound_lat + latency_increase_from_base;

  // Clamp latency to minimum value in the curve
  if (lower_bound_lat == 0)
    latency_value = upper_bound_lat;

  DPRINTF(BwLatCtrl, "Got Latency = %f. BW = [%f, %f], LAT = [%f, %f]\n",
          latency_value, lower_bound_bw, upper_bound_bw, lower_bound_lat,
          upper_bound_lat);

  latency_overflow_factor = std::max(0.0, latency_overflow_factor - 0.01);

  return Cycles(latency_value);
}
// Stats
BwLatCtrl::BwLatCtrlStats::BwLatCtrlStats(BwLatCtrl &_ctrl)
    : statistics::Group(&_ctrl), ctrl(_ctrl),

      ADD_STAT(totalDispatchedLatency, statistics::units::Cycle::get(),
               "Total Latency dispatched by the BwLatController"),
      ADD_STAT(
          latencyDispatchedCount, statistics::units::Count::get(),
          "Number of times a response got dispatched by the BwLatController"),

      ADD_STAT(totalRequestedBandwidth, statistics::units::Byte::get(),
               "Total bandwidth requested from the controller"),
      ADD_STAT(bandwidthRequestedCount, statistics::units::Count::get(),
               "Number of times bandiwdth was exhamined"),
      ADD_STAT(totalDispatchedBandwidth, statistics::units::Byte::get(),
               "Total bandwidth dispatched from the controller"),
      ADD_STAT(bandwidthDispatchedCount, statistics::units::Count::get(),
               "Number of times bandiwdth-dispatched was exhamined") {}

void BwLatCtrl::BwLatCtrlStats::regStats() {
  using namespace statistics;

  totalDispatchedLatency = 0;
  latencyDispatchedCount = 0;

  totalRequestedBandwidth = 0;
  bandwidthRequestedCount = 0;

  totalDispatchedBandwidth = 0;
  bandwidthDispatchedCount = 0;
}
} // namespace memory
} // namespace gem5
