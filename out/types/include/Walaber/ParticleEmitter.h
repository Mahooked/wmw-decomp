// Recovered from Walaber::ParticleEmitter. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__PARTICLEEMITTER_H
#define WMW_WALABER__PARTICLEEMITTER_H

#include <stdint.h>

namespace Walaber {
struct ParticleEmitter {
    // size 464, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad128[120];
    uint64_t f_0x80;
    uint64_t f_0x88;
    uint64_t f_0x90;
    uint64_t f_0x98;
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    int32_t f_0xb0;
    int32_t f_0xb4;
    int32_t f_0xb8;
    int32_t f_0xbc;
    int32_t f_0xc0;
    int32_t f_0xc4;
    int32_t f_0xc8;
    int32_t f_0xcc;
    int32_t f_0xd0;
    int32_t f_0xd4;
    int32_t f_0xd8;
    int32_t f_0xdc;
    uint64_t f_0xe0;
    uint64_t f_0xe8;
    uint64_t f_0xf0;
    float f_0xf8;
    uint8_t _pad256[4];
    float f_0x100;
    uint8_t _pad264[4];
    float f_0x108;
    float f_0x10c;
    float f_0x110;
    float f_0x114;
    float f_0x118;
    float f_0x11c;
    float f_0x120;
    float f_0x124;
    float f_0x128;
    float f_0x12c;
    float f_0x130;
    float f_0x134;
    uint64_t f_0x138;
    float f_0x140;
    uint8_t _pad328[4];
    uint8_t f_0x148;
    uint8_t f_0x149;
    uint8_t _pad336[6];
    uint64_t f_0x150;
    uint8_t _pad352[8];
    float f_0x160;
    uint8_t _pad360[4];
    float f_0x168;
    int32_t f_0x16c;
    uint8_t _pad456[88];
    uint8_t f_0x1c8;
    uint8_t f_0x1c9;
    uint8_t f_0x1ca;
    uint8_t _tail[5];
};

}  // namespace Walaber
#endif
