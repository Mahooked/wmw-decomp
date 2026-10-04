// Recovered from Walaber::Sprite. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SPRITE_H
#define WMW_WALABER__SPRITE_H

#include <stdint.h>

namespace Walaber {
struct Sprite {
    // size 216, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    uint8_t _pad144[112];
    uint64_t f_0x90;
    uint64_t f_0x98;
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    int32_t f_0xb0;
    uint8_t _pad184[4];
    uint64_t f_0xb8;
    uint8_t _pad200[8];
    uint8_t f_0xc8;
    uint8_t f_0xc9;
    uint8_t _pad205[3];
    uint8_t f_0xcd;
    uint8_t _pad208[2];
    uint64_t f_0xd0;
};

}  // namespace Walaber
#endif
