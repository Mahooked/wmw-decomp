// Recovered from Walaber::CameraController. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__CAMERACONTROLLER_H
#define WMW_WALABER__CAMERACONTROLLER_H

#include <stdint.h>

namespace Walaber {
struct CameraController {
    // size 176, align 8, confidence high
    uint64_t isAnimating;  // named from isAnimating
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint8_t _pad48[8];
    uint64_t f_0x30;
    uint64_t f_0x38;
    uint8_t _pad72[8];
    uint64_t f_0x48;
    uint64_t f_0x50;
    uint8_t _pad96[8];
    uint64_t f_0x60;
    uint64_t f_0x68;
    uint8_t _pad120[8];
    uint64_t f_0x78;
    uint64_t f_0x80;
    uint8_t _pad144[8];
    uint64_t f_0x90;
    uint64_t f_0x98;
    uint8_t _pad168[8];
    uint8_t f_0xa8;
    uint8_t _pad172[3];
    int32_t f_0xac;
};

}  // namespace Walaber
#endif
