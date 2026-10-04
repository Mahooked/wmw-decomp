// Recovered from WaterConcept::Screen_InAppPurchase. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SCREEN_INAPPPURCHASE_H
#define WMW_WATERCONCEPT__SCREEN_INAPPPURCHASE_H

#include <stdint.h>

namespace WaterConcept {
struct Screen_InAppPurchase {
    // size 608, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint8_t _pad32[8];
    uint64_t f_0x20;
    uint8_t _pad144[104];
    uint64_t f_0x90;
    uint8_t _pad156[4];
    int32_t f_0x9c;
    uint8_t _pad168[8];
    uint8_t f_0xa8;
    uint8_t _pad176[7];
    uint64_t f_0xb0;
    uint64_t f_0xb8;
    uint8_t f_0xc0;
    uint8_t _pad200[7];
    uint64_t f_0xc8;
    uint64_t f_0xd0;
    uint8_t _pad240[24];
    uint8_t f_0xf0;
    uint8_t _pad248[7];
    uint64_t f_0xf8;
    uint64_t f_0x100;
    uint8_t f_0x108;
    uint8_t _pad272[7];
    uint64_t f_0x110;
    uint64_t f_0x118;
    uint8_t _pad328[40];
    int32_t f_0x148;
    uint8_t f_0x14c;
    uint8_t _pad336[3];
    int32_t f_0x150;
    uint8_t f_0x154;
    uint8_t f_0x155;
    uint8_t f_0x156;
    uint8_t f_0x157;
    int32_t f_0x158;
    uint8_t _pad384[36];
    uint64_t f_0x180;
    uint8_t _pad400[8];
    int32_t f_0x190;
    uint8_t f_0x194;
    uint8_t f_0x195;
    uint8_t _pad407[1];
    uint8_t f_0x197;
    uint8_t _pad412[4];
    float f_0x19c;
    uint64_t f_0x1a0;
    uint64_t f_0x1a8;
    float f_0x1b0;
    uint8_t _pad448[12];
    uint8_t f_0x1c0;
    uint8_t _pad450[1];
    uint8_t f_0x1c2;
    uint8_t _pad452[1];
    uint8_t f_0x1c4;
    uint8_t f_0x1c5;
    uint8_t f_0x1c6;
    uint8_t f_0x1c7;
    uint8_t f_0x1c8;
    uint8_t f_0x1c9;
    uint8_t f_0x1ca;
    uint8_t f_0x1cb;
    uint8_t f_0x1cc;
    uint8_t _pad464[3];
    int32_t f_0x1d0;
    uint8_t _pad472[4];
    uint8_t f_0x1d8;
    uint8_t _pad488[15];
    uint64_t f_0x1e8;
    uint8_t f_0x1f0;
    uint8_t _pad512[15];
    uint64_t f_0x200;
    int32_t f_0x208;
    uint8_t _pad528[4];
    uint8_t f_0x210;
    uint8_t _pad544[15];
    uint64_t f_0x220;
    uint8_t f_0x228;
    uint8_t _pad568[15];
    uint64_t f_0x238;
    uint8_t _pad604[28];
    uint8_t f_0x25c;
    uint8_t f_0x25d;
    uint8_t _tail[2];
};

}  // namespace WaterConcept
#endif
