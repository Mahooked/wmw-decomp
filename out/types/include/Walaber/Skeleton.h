// Recovered from Walaber::Skeleton. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__SKELETON_H
#define WMW_WALABER__SKELETON_H

#include <stdint.h>

namespace Walaber {
struct Skeleton {
    // size 352, align 8, confidence high
    uint64_t f_0x0;
    uint8_t f_0x8;
    uint8_t _pad16[7];
    uint64_t f_0x10;
    uint64_t f_0x18;
    int32_t f_0x20;
    uint8_t _pad96[60];
    float f_0x60;
    uint8_t _pad144[44];
    uint64_t f_0x90;
    uint8_t _pad160[8];
    uint64_t f_0xa0;
    uint64_t f_0xa8;
    uint8_t _pad184[8];
    uint64_t f_0xb8;
    uint64_t f_0xc0;
    uint8_t _pad208[8];
    uint64_t f_0xd0;
    uint64_t f_0xd8;
    uint8_t _pad312[88];
    int32_t f_0x138;
    uint8_t _pad320[4];
    uint64_t f_0x140;
    uint8_t _pad336[8];
    uint64_t f_0x150;
    uint8_t f_0x158;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
