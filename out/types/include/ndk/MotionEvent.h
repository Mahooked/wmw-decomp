// Recovered from ndk::MotionEvent. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_NDK__MOTIONEVENT_H
#define WMW_NDK__MOTIONEVENT_H

#include <stdint.h>

namespace ndk {
struct MotionEvent {
    // size 128, align 8, confidence high
    int32_t f_0x0;
    uint8_t _pad8[4];
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint64_t f_0x28;
    uint64_t f_0x30;
    uint64_t f_0x38;
    uint64_t f_0x40;
    uint64_t f_0x48;
    uint64_t f_0x50;
    uint64_t f_0x58;
    uint64_t f_0x60;
    uint64_t f_0x68;
    uint64_t f_0x70;
    uint64_t f_0x78;
};

}  // namespace ndk
#endif
