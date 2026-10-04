// Recovered from Walaber::SoundManager. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SOUNDMANAGER_H
#define WMW_WALABER__SOUNDMANAGER_H

#include <stdint.h>

namespace Walaber {
struct SoundManager {
    // size 408, align 8, confidence high
    uint8_t _pad8[8];
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint8_t _pad56[16];
    uint64_t f_0x38;
    uint8_t _pad80[16];
    uint64_t f_0x50;
    uint8_t _pad104[16];
    uint64_t f_0x68;
    uint64_t f_0x70;
    uint8_t _pad160[40];
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint64_t f_0xb8;
    uint8_t _pad208[16];
    uint64_t f_0xd0;
    uint8_t _pad240[24];
    int32_t f_0xf0;
    uint8_t _pad312[68];
    uint64_t f_0x138;
    uint64_t f_0x140;
    uint8_t _pad384[56];
    int32_t f_0x180;
    uint8_t _pad392[4];
    uint64_t f_0x188;
    uint8_t f_0x190;
    uint8_t _pad402[1];
    uint8_t f_0x192;
    uint8_t _tail[5];
};

}  // namespace Walaber
#endif
