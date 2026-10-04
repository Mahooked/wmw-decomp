// Recovered from ndk::AccelerometerEvent. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_NDK__ACCELEROMETEREVENT_H
#define WMW_NDK__ACCELEROMETEREVENT_H

#include <stdint.h>

namespace ndk {
struct AccelerometerEvent {
    // size 12, align 4, confidence med
    float f_0x0;
    uint8_t _pad8[4];
    int32_t f_0x8;
};

}  // namespace ndk
#endif
