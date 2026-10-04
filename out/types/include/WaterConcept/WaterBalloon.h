// Recovered from WaterConcept::WaterBalloon. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__WATERBALLOON_H
#define WMW_WATERCONCEPT__WATERBALLOON_H

#include <stdint.h>

namespace WaterConcept {
struct WaterBalloon {
    // size 1264, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad220[212];
    uint8_t f_0xdc;
    uint8_t _pad400[179];
    uint64_t f_0x190;
    uint8_t _pad936[528];
    uint64_t f_0x3a8;
    uint8_t _pad1112[168];
    uint64_t f_0x458;
    uint64_t f_0x460;
    uint8_t _pad1136[8];
    float f_0x470;
    float f_0x474;
    uint8_t _pad1176[32];
    uint64_t f_0x498;
    int32_t f_0x4a0;
    int32_t f_0x4a4;
    uint8_t _pad1244[52];
    uint8_t f_0x4dc;
    uint8_t _pad1248[3];
    float f_0x4e0;
    uint8_t _pad1256[4];
    uint64_t f_0x4e8;
};

}  // namespace WaterConcept
#endif
