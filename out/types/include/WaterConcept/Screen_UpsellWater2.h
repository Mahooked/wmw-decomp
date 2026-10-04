// Recovered from WaterConcept::Screen_UpsellWater2. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_UPSELLWATER2_H
#define WMW_WATERCONCEPT__SCREEN_UPSELLWATER2_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_UpsellWater2 {
    // size 288, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad168[16];
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint8_t _pad240[56];
    uint8_t f_0xf0;
    uint8_t _pad248[7];
    uint64_t f_0xf8;
    uint8_t _pad264[8];
    uint8_t f_0x108;
    uint8_t _pad280[15];
    uint64_t f_0x118;
};

}  // namespace WaterConcept
#endif
