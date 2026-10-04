// Recovered from Walaber::Camera. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__CAMERA_H
#define WMW_WALABER__CAMERA_H

#include <stdint.h>

namespace Walaber {
struct Camera {
    // size 144, align 8, confidence high
    float f_0x0;
    uint8_t _pad8[4];
    float f_0x8;
    float f_0xc;
    uint64_t f_0x10;
    uint64_t f_0x18;
    uint8_t _pad40[8];
    uint64_t f_0x28;
    uint64_t f_0x30;
    uint8_t _pad64[8];
    uint64_t f_0x40;
    uint64_t f_0x48;
    uint8_t _pad88[8];
    uint64_t f_0x58;
    uint64_t f_0x60;
    uint8_t _pad112[8];
    uint64_t f_0x70;
    uint64_t f_0x78;
    uint8_t _pad136[8];
    uint8_t f_0x88;
    uint8_t _pad140[3];
    float f_0x8c;
};

}  // namespace Walaber
#endif
