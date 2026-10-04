// Recovered from WaterConcept::Screen_Processing. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_PROCESSING_H
#define WMW_WATERCONCEPT__SCREEN_PROCESSING_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_Processing {
    // size 256, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad156[4];
    int32_t f_0x9c;
    uint8_t _pad176[16];
    float f_0xb0;
    uint8_t _pad184[4];
    uint8_t f_0xb8;
    uint8_t _pad208[23];
    uint64_t f_0xd0;
    uint8_t _pad232[16];
    uint64_t f_0xe8;
    uint8_t _pad252[12];
    uint8_t f_0xfc;
    uint8_t f_0xfd;
    uint8_t _pad255[1];
    uint8_t f_0xff;
};

}  // namespace WaterConcept
#endif
