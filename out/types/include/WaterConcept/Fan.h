// Recovered from WaterConcept::Fan. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__FAN_H
#define WMW_WATERCONCEPT__FAN_H

#include <stdint.h>

namespace WaterConcept {
struct Fan {
    // size 1096, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad376[368];
    uint64_t f_0x178;
    uint8_t _pad400[16];
    uint64_t f_0x190;
    uint64_t f_0x198;
    uint8_t _pad776[360];
    float f_0x308;
    uint8_t _pad936[156];
    uint8_t f_0x3a8;
    uint8_t _pad940[3];
    int32_t f_0x3ac;
    uint64_t f_0x3b0;
    uint64_t f_0x3b8;
    uint8_t _pad968[8];
    uint64_t f_0x3c8;
    uint64_t f_0x3d0;
    uint8_t _pad1024[40];
    uint64_t f_0x400;
    uint64_t f_0x408;
    uint64_t f_0x410;
    uint8_t _pad1056[8];
    uint64_t f_0x420;
    uint64_t f_0x428;
    uint8_t _pad1080[8];
    uint64_t f_0x438;
    uint64_t f_0x440;
};

}  // namespace WaterConcept
#endif
