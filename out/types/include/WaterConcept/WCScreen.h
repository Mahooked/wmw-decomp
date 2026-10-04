// Recovered from WaterConcept::WCScreen. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__WCSCREEN_H
#define WMW_WATERCONCEPT__WCSCREEN_H

#include <stdint.h>

namespace WaterConcept {
struct WCScreen {
    // size 40, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
};

}  // namespace WaterConcept
#endif
