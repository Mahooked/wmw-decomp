// Recovered from Walaber::Texture. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TEXTURE_H
#define WMW_WALABER__TEXTURE_H

#include <stdint.h>

namespace Walaber {
struct Texture {
    // size 128, align 16, confidence high
    uint64_t f_0x0;
    uint8_t _pad32[24];
    uint64_t f_0x20;
    int32_t f_0x28;
    uint8_t f_0x2c;
    uint8_t f_0x2d;
    uint8_t f_0x2e;
    uint8_t f_0x2f;
    uint64_t f_0x30;
    uint8_t _pad64[8];
    uint64_t f_0x40;
    uint8_t _pad96[24];
    uint64_t f_0x60;
    uint8_t _pad112[8];
    uint64_t f_0x70;
    int32_t f_0x78;
    float f_0x7c;
};

}  // namespace Walaber
#endif
