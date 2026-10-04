// Recovered from Walaber::Texture2D. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TEXTURE2D_H
#define WMW_WALABER__TEXTURE2D_H

#include <stdint.h>

namespace Walaber {
struct Texture2D {
    // size 232, align 8, confidence high
    uint64_t f_0x0;
    uint8_t f_0x8;
    uint8_t _pad16[7];
    uint64_t f_0x10;
    uint64_t f_0x18;
    uint8_t _pad120[88];
    int32_t f_0x78;
    uint32_t f_0x7c;
    uint8_t _pad132[4];
    uint32_t f_0x84;
    uint8_t _pad168[32];
    uint64_t f_0xa8;
    uint64_t f_0xb0;
    uint8_t _pad192[8];
    uint64_t f_0xc0;
    uint8_t _pad208[8];
    uint64_t f_0xd0;
    uint8_t _pad224[8];
    int32_t f_0xe0;
    int32_t f_0xe4;
};

}  // namespace Walaber
#endif
