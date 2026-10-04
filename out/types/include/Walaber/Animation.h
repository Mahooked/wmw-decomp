// Recovered from Walaber::Animation. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__ANIMATION_H
#define WMW_WALABER__ANIMATION_H

#include <stdint.h>

namespace Walaber {
struct Animation {
    // size 264, align 8, confidence high
    float f_0x0;
    uint8_t _pad24[20];
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint64_t f_0x28;
    uint64_t f_0x30;
    uint64_t f_0x38;
    uint64_t f_0x40;
    uint64_t f_0x48;
    uint64_t f_0x50;
    uint64_t f_0x58;
    uint64_t f_0x60;
    uint64_t f_0x68;
    uint64_t f_0x70;
    uint64_t f_0x78;
    uint64_t f_0x80;
    uint64_t f_0x88;
    uint64_t f_0x90;
    uint64_t f_0x98;
    uint8_t _pad168[8];
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint64_t f_0xb8;
    int32_t f_0xc0;
    int32_t f_0xc4;
    float f_0xc8;
    float f_0xcc;
    float f_0xd0;
    int32_t f_0xd4;
    int32_t f_0xd8;
    int32_t f_0xdc;
    int32_t f_0xe0;
    int32_t f_0xe4;
    uint64_t f_0xe8;
    uint64_t f_0xf0;
    uint8_t _pad256[8];
    uint8_t f_0x100;
    uint8_t f_0x101;
    uint8_t f_0x102;
    uint8_t f_0x103;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
