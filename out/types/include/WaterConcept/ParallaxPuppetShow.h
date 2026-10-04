// Recovered from WaterConcept::ParallaxPuppetShow. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__PARALLAXPUPPETSHOW_H
#define WMW_WATERCONCEPT__PARALLAXPUPPETSHOW_H

#include <stdint.h>

namespace WaterConcept {
struct ParallaxPuppetShow {
    // size 640, align 8, confidence high
    uint8_t f_0x0;
    uint8_t f_0x1;
    uint8_t _pad4[2];
    float f_0x4;
    uint8_t f_0x8;
    uint8_t _pad24[15];
    int32_t f_0x18;
    uint8_t _pad352[324];
    uint64_t f_0x160;
    uint64_t f_0x168;
    uint8_t _pad480[112];
    uint64_t f_0x1e0;
    uint64_t f_0x1e8;
    uint8_t _pad504[8];
    uint64_t f_0x1f8;
    uint64_t f_0x200;
    uint8_t _pad528[8];
    uint64_t f_0x210;
    uint64_t f_0x218;
    uint8_t _pad552[8];
    uint64_t f_0x228;
    uint64_t f_0x230;
    uint8_t _pad576[8];
    uint64_t f_0x240;
    uint8_t _pad600[16];
    uint64_t f_0x258;
    int32_t f_0x260;
    int32_t f_0x264;
    uint64_t f_0x268;
    uint8_t _pad632[8];
    uint8_t f_0x278;
    uint8_t _tail[7];
};

}  // namespace WaterConcept
#endif
