// Recovered from WaterConcept::Screen_PerformanceTest. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_PERFORMANCETEST_H
#define WMW_WATERCONCEPT__SCREEN_PERFORMANCETEST_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_PerformanceTest {
    // size 168, align 8, confidence high
    uint8_t _pad16[16];
    uint64_t f_0x10;
    uint8_t _pad144[120];
    int32_t f_0x90;
    uint8_t _pad162[14];
    uint8_t f_0xa2;
    uint8_t _tail[5];
};

}  // namespace WaterConcept
#endif
