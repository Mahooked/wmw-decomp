// Recovered from WaterConcept::Grid. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__GRID_H
#define WMW_WATERCONCEPT__GRID_H

#include <stdint.h>

namespace WaterConcept {
struct Grid {
    // size 48, align 4, confidence high
    float f_0x0;
    uint8_t _pad8[4];
    float f_0x8;
    float f_0xc;
    int32_t f_0x10;
    int32_t f_0x14;
    float f_0x18;
    float f_0x1c;
    int32_t f_0x20;
    int32_t f_0x24;
    int32_t f_0x28;
    int32_t f_0x2c;
};

}  // namespace WaterConcept
#endif
