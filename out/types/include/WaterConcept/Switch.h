// Recovered from WaterConcept::Switch. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SWITCH_H
#define WMW_WATERCONCEPT__SWITCH_H

#include <stdint.h>

namespace WaterConcept {
struct Switch {
    // size 1048, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad400[392];
    uint64_t f_0x190;
    uint64_t f_0x198;
    uint8_t _pad936[520];
    int32_t f_0x3a8;
    uint8_t f_0x3ac;
    uint8_t _pad944[3];
    int32_t f_0x3b0;
    int32_t f_0x3b4;
    uint64_t f_0x3b8;
    uint64_t f_0x3c0;
    uint8_t _pad976[8];
    uint64_t f_0x3d0;
    uint64_t f_0x3d8;
    uint64_t f_0x3e0;
    uint64_t f_0x3e8;
    uint64_t f_0x3f0;
    uint8_t _pad1024[8];
    float f_0x400;
    float f_0x404;
    uint8_t _pad1036[4];
    int32_t f_0x40c;
    uint64_t f_0x410;
};

}  // namespace WaterConcept
#endif
