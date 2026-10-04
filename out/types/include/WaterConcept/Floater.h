// Recovered from WaterConcept::Floater. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__FLOATER_H
#define WMW_WATERCONCEPT__FLOATER_H

#include <stdint.h>

namespace WaterConcept {
struct Floater {
    // size 1112, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad224[216];
    uint64_t f_0xe0;
    uint64_t f_0xe8;
    uint8_t _pad936[696];
    uint64_t f_0x3a8;
    float f_0x3b0;
    uint8_t _pad952[4];
    uint64_t f_0x3b8;
    uint64_t f_0x3c0;
    uint8_t _pad976[8];
    uint64_t f_0x3d0;
    uint8_t _pad1024[40];
    float f_0x400;
    uint8_t _pad1040[12];
    uint64_t f_0x410;
    uint64_t f_0x418;
    uint8_t _pad1064[8];
    uint64_t f_0x428;
    uint64_t f_0x430;
    float f_0x438;
    uint8_t _pad1092[8];
    uint8_t f_0x444;
    uint8_t _pad1104[11];
    float f_0x450;
    float f_0x454;
};

}  // namespace WaterConcept
#endif
