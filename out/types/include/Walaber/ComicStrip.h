// Recovered from Walaber::ComicStrip. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__COMICSTRIP_H
#define WMW_WALABER__COMICSTRIP_H

#include <stdint.h>

namespace Walaber {
struct ComicStrip {
    // size 408, align 8, confidence high
    int32_t f_0x0;
    int32_t f_0x4;
    float f_0x8;
    uint8_t _pad16[4];
    uint64_t f_0x10;
    uint64_t f_0x18;
    uint8_t _pad40[8];
    uint64_t f_0x28;
    uint64_t f_0x30;
    uint8_t _pad88[32];
    uint64_t f_0x58;
    uint64_t f_0x60;
    uint8_t _pad112[8];
    uint64_t f_0x70;
    uint64_t f_0x78;
    uint8_t _pad136[8];
    uint64_t f_0x88;
    uint64_t f_0x90;
    uint8_t _pad160[8];
    int32_t f_0xa0;
    int32_t f_0xa4;
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint8_t _pad192[8];
    uint64_t f_0xc0;
    uint64_t f_0xc8;
    uint8_t _pad216[8];
    uint64_t f_0xd8;
    uint64_t f_0xe0;
    uint8_t _pad240[8];
    uint64_t f_0xf0;
    uint64_t f_0xf8;
    uint8_t _pad264[8];
    uint64_t f_0x108;
    uint64_t f_0x110;
    uint8_t _pad288[8];
    uint64_t f_0x120;
    uint64_t f_0x128;
    uint8_t _pad312[8];
    uint64_t f_0x138;
    uint64_t f_0x140;
    uint8_t _pad336[8];
    uint64_t f_0x150;
    uint64_t f_0x158;
    uint8_t _pad360[8];
    uint64_t f_0x168;
    uint64_t f_0x170;
    uint8_t _pad384[8];
    uint64_t f_0x180;
    uint64_t f_0x188;
    uint64_t f_0x190;
};

}  // namespace Walaber
#endif
