// Recovered from Walaber::TextureSettings. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__TEXTURESETTINGS_H
#define WMW_WALABER__TEXTURESETTINGS_H

#include <stdint.h>

namespace Walaber {
struct TextureSettings {
    // size 88, align 8, confidence high
    uint64_t f_0x0;
    int32_t f_0x8;
    uint8_t f_0xc;
    uint8_t f_0xd;
    uint8_t f_0xe;
    uint8_t f_0xf;
    float f_0x10;
    uint8_t _pad24[4];
    int32_t f_0x18;
    int32_t f_0x1c;
    uint64_t f_0x20;
    uint8_t _pad64[24];
    uint8_t f_0x40;
    uint8_t _pad80[15];
    uint64_t f_0x50;
};

}  // namespace Walaber
#endif
