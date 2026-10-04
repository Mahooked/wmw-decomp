// Recovered from Walaber::Widget_ScrollableSet. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__WIDGET_SCROLLABLESET_H
#define WMW_WALABER__WIDGET_SCROLLABLESET_H

#include <stdint.h>

namespace Walaber {
struct Widget_ScrollableSet {
    // size 392, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad256[248];
    uint64_t f_0x100;
    int32_t f_0x108;
    int32_t currentIndex;  // named from getCurrentIndex
    int32_t f_0x110;
    int32_t f_0x114;
    float f_0x118;
    uint8_t _pad288[4];
    float distanceBetween;  // named from setDistanceBetween
    int32_t f_0x124;
    int32_t f_0x128;
    uint8_t _pad304[4];
    int32_t f_0x130;
    float f_0x134;
    float f_0x138;
    uint8_t _pad320[4];
    uint64_t f_0x140;
    uint64_t f_0x148;
    uint8_t _pad344[8];
    uint64_t f_0x158;
    uint64_t f_0x160;
    uint8_t _pad368[8];
    uint64_t f_0x170;
    uint64_t camera;  // named from setCamera
    uint8_t cameraMode;  // named from getCameraMode,setCameraMode
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
