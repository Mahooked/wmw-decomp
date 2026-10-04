// Recovered from WaterConcept::Screen_Loading. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_LOADING_H
#define WMW_WATERCONCEPT__SCREEN_LOADING_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Loading {
    // size 24, align 8, confidence high
    int32_t f_0x0;
    uint8_t f_0x4;
    uint8_t _pad16[11];
    uint64_t f_0x10;
};

}  // namespace WaterConcept
#endif
