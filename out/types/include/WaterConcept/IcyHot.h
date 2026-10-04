// Recovered from WaterConcept::IcyHot. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__ICYHOT_H
#define WMW_WATERCONCEPT__ICYHOT_H

#include <stdint.h>

namespace WaterConcept {
struct IcyHot {
    // size 1136, align 8, confidence high
    float f_0x0;
    uint8_t _pad400[396];
    uint64_t f_0x190;
    uint8_t _pad936[528];
    uint64_t f_0x3a8;
    uint64_t f_0x3b0;
    uint64_t f_0x3b8;
    uint64_t f_0x3c0;
    uint64_t f_0x3c8;
    uint64_t f_0x3d0;
    uint64_t f_0x3d8;
    uint8_t _pad996[4];
    int32_t f_0x3e4;
    int32_t f_0x3e8;
    uint8_t _pad1008[4];
    float f_0x3f0;
    uint8_t _pad1016[4];
    uint64_t f_0x3f8;
    float f_0x400;
    uint8_t _pad1080[52];
    int32_t f_0x438;
    int32_t f_0x43c;
    uint8_t _pad1092[4];
    int32_t f_0x444;
    int32_t f_0x448;
    uint8_t _pad1104[4];
    uint64_t f_0x450;
    uint8_t _pad1120[8];
    int32_t f_0x460;
    uint8_t f_0x464;
    uint8_t _pad1128[3];
    float f_0x468;
    uint8_t f_0x46c;
    uint8_t _tail[3];
};

}  // namespace WaterConcept
#endif
