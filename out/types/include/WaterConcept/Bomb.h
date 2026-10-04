// Recovered from WaterConcept::Bomb. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__BOMB_H
#define WMW_WATERCONCEPT__BOMB_H

#include <stdint.h>

namespace WaterConcept {
struct Bomb {
    // size 976, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad400[392];
    uint64_t f_0x190;
    uint8_t _pad936[528];
    int32_t f_0x3a8;
    int32_t f_0x3ac;
    int32_t f_0x3b0;
    uint8_t _pad952[4];
    uint64_t f_0x3b8;
    uint8_t _pad968[8];
    int32_t f_0x3c8;
    uint8_t _tail[4];
};

}  // namespace WaterConcept
#endif
