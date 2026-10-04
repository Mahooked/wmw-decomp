// Recovered from Walaber::RenderTexture2D. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__RENDERTEXTURE2D_H
#define WMW_WALABER__RENDERTEXTURE2D_H

#include <stdint.h>

namespace Walaber {
struct RenderTexture2D {
    // size 216, align 8, confidence high
    double f_0x0;
    uint8_t _pad120[112];
    int32_t f_0x78;
    int32_t f_0x7c;
    int32_t f_0x80;
    uint32_t f_0x84;
    uint8_t _pad140[4];
    int32_t f_0x8c;
    int32_t f_0x90;
    uint32_t f_0x94;
    uint8_t _pad156[4];
    uint32_t f_0x9c;
    uint8_t _pad188[28];
    int32_t f_0xbc;
    int32_t f_0xc0;
    int32_t f_0xc4;
    int32_t f_0xc8;
    int32_t f_0xcc;
    int32_t f_0xd0;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
