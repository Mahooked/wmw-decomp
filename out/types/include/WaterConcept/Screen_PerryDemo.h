// Recovered from WaterConcept::Screen_PerryDemo. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_PERRYDEMO_H
#define WMW_WATERCONCEPT__SCREEN_PERRYDEMO_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_PerryDemo {
    // size 264, align 8, confidence high
    int32_t f_0x0;
    uint8_t _pad16[12];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad157[5];
    uint8_t f_0x9d;
    uint8_t _pad208[50];
    uint8_t f_0xd0;
    uint8_t _pad210[1];
    uint8_t f_0xd2;
    uint8_t _pad212[1];
    int32_t f_0xd4;
    uint8_t f_0xd8;
    uint8_t _pad224[7];
    uint64_t f_0xe0;
    uint64_t f_0xe8;
    uint8_t f_0xf0;
    uint8_t _pad248[7];
    uint64_t f_0xf8;
    uint64_t f_0x100;
};

}  // namespace WaterConcept
#endif
