// Recovered from WaterConcept::Screen_Sunset. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_SUNSET_H
#define WMW_WATERCONCEPT__SCREEN_SUNSET_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Sunset {
    // size 192, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad184[32];
    uint8_t f_0xb8;
    uint8_t _tail[7];
};

}  // namespace WaterConcept
#endif
