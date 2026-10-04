// Recovered from WaterConcept::Screen_LevelSelect. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_LEVELSELECT_H
#define WMW_WATERCONCEPT__SCREEN_LEVELSELECT_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_LevelSelect {
    // size 744, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad192[40];
    uint8_t f_0xc0;
    uint8_t _pad248[55];
    uint64_t f_0xf8;
    uint8_t _pad272[16];
    uint64_t f_0x110;
    uint64_t f_0x118;
    uint8_t _pad296[8];
    uint64_t f_0x128;
    uint8_t f_0x130;
    uint8_t f_0x131;
    uint8_t f_0x132;
    uint8_t f_0x133;
    uint8_t _pad312[4];
    int32_t f_0x138;
    uint8_t _pad384[68];
    uint64_t f_0x180;
    uint64_t f_0x188;
    uint8_t _pad432[32];
    int32_t f_0x1b0;
    uint8_t _pad440[4];
    uint8_t f_0x1b8;
    uint8_t _pad448[7];
    uint64_t f_0x1c0;
    uint8_t _pad464[8];
    uint64_t f_0x1d0;
    uint8_t _pad480[8];
    float f_0x1e0;
    float f_0x1e4;
    uint64_t f_0x1e8;
    uint64_t f_0x1f0;
    uint64_t f_0x1f8;
    uint64_t f_0x200;
    uint64_t f_0x208;
    uint64_t f_0x210;
    uint64_t f_0x218;
    uint8_t _pad560[16];
    uint64_t f_0x230;
    uint64_t f_0x238;
    uint8_t _pad584[8];
    int32_t f_0x248;
    int32_t f_0x24c;
    int32_t f_0x250;
    int32_t f_0x254;
    int32_t f_0x258;
    int32_t f_0x25c;
    uint64_t f_0x260;
    uint64_t f_0x268;
    uint64_t f_0x270;
    uint64_t f_0x278;
    uint64_t f_0x280;
    float f_0x288;
    int32_t f_0x28c;
    int32_t f_0x290;
    float f_0x294;
    int32_t f_0x298;
    int32_t f_0x29c;
    uint64_t f_0x2a0;
    uint64_t f_0x2a8;
    uint8_t _pad696[8];
    uint64_t f_0x2b8;
    uint64_t f_0x2c0;
    uint8_t _pad720[8];
    uint8_t f_0x2d0;
    uint8_t _pad728[7];
    uint64_t f_0x2d8;
    uint64_t f_0x2e0;
};

}  // namespace WaterConcept
#endif
