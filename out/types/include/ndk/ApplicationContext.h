// Recovered from ndk::ApplicationContext. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_NDK__APPLICATIONCONTEXT_H
#define WMW_NDK__APPLICATIONCONTEXT_H

#include <stdint.h>

namespace ndk {
struct ApplicationContext {
    // size 232, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad16[8];
    uint64_t f_0x10;
    uint64_t activity;  // named from setActivity
    uint8_t f_0x20;
    uint8_t _pad41[8];
    uint8_t f_0x29;
    uint8_t _pad43[1];
    uint8_t f_0x2b;
    uint8_t _pad48[4];
    uint64_t f_0x30;
    uint8_t _pad96[40];
    uint8_t f_0x60;
    uint8_t _pad104[7];
    uint64_t f_0x68;
    uint64_t f_0x70;
    uint8_t f_0x78;
    uint8_t _pad136[15];
    uint64_t f_0x88;
    float f_0x90;
    float f_0x94;
    float f_0x98;
    float f_0x9c;
    uint8_t f_0xa0;
    uint8_t _pad164[3];
    float f_0xa4;
    int32_t f_0xa8;
    uint8_t _pad176[4];
    uint8_t f_0xb0;
    uint8_t _pad192[15];
    uint64_t f_0xc0;
    uint8_t f_0xc8;
    uint8_t _pad204[3];
    float displayDensity;  // named from setDisplayDensity
    uint8_t f_0xd0;
    uint8_t _pad224[15];
    uint64_t f_0xe0;
};

}  // namespace ndk
#endif
