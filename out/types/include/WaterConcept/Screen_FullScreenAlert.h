// Recovered from WaterConcept::Screen_FullScreenAlert. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_FULLSCREENALERT_H
#define WMW_WATERCONCEPT__SCREEN_FULLSCREENALERT_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_FullScreenAlert {
    // size 360, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad16[15];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad168[128];
    uint8_t f_0xa8;
    uint8_t _pad184[15];
    uint64_t f_0xb8;
    uint8_t f_0xc0;
    uint8_t _pad208[15];
    uint64_t f_0xd0;
    uint8_t f_0xd8;
    uint8_t _pad224[7];
    uint64_t f_0xe0;
    uint64_t f_0xe8;
    uint8_t f_0xf0;
    uint8_t _pad248[7];
    uint64_t f_0xf8;
    uint64_t f_0x100;
    uint8_t f_0x108;
    uint8_t _pad272[7];
    uint64_t f_0x110;
    uint64_t f_0x118;
    uint8_t f_0x120;
    uint8_t _pad292[3];
    float f_0x124;
    float f_0x128;
    uint8_t f_0x12c;
    uint8_t f_0x12d;
    uint8_t f_0x12e;
    uint8_t f_0x12f;
    uint8_t f_0x130;
    uint8_t _pad308[3];
    int32_t f_0x134;
    uint64_t f_0x138;
    uint64_t f_0x140;
    uint8_t _pad336[8];
    int32_t f_0x150;
    uint8_t _pad344[4];
    uint64_t f_0x158;
    int32_t f_0x160;
    uint8_t f_0x164;
    uint8_t _tail[3];
};

}  // namespace WaterConcept
#endif
