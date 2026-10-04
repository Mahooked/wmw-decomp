// Recovered from Walaber::SpriteAnimation. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SPRITEANIMATION_H
#define WMW_WALABER__SPRITEANIMATION_H

#include <stdint.h>

namespace Walaber {
struct SpriteAnimation {
    // size 192, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad8[7];
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint8_t f_0x18;
    uint8_t _pad28[3];
    int32_t f_0x1c;
    float f_0x20;
    uint8_t _pad40[4];
    uint64_t f_0x28;
    uint64_t f_0x30;
    uint64_t f_0x38;
    int32_t f_0x40;
    float f_0x44;
    int32_t f_0x48;
    uint32_t f_0x4c;
    uint8_t _pad84[4];
    int32_t f_0x54;
    int32_t f_0x58;
    uint8_t _pad112[20];
    uint64_t f_0x70;
    uint64_t f_0x78;
    uint64_t f_0x80;
    uint64_t f_0x88;
    uint64_t f_0x90;
    uint8_t _pad160[8];
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint64_t f_0xb8;
};

}  // namespace Walaber
#endif
