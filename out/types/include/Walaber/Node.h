// Recovered from Walaber::Node. Offsets and element types come from load/store
// evidence in the binary; the names do not, and are inferred
// from the accessor symbols noted against them. Everything else
// is named after the offset it sits at.
#ifndef WMW_WALABER__NODE_H
#define WMW_WALABER__NODE_H

#include <stdint.h>

namespace Walaber {
struct Node {
    // size 128, align 8, confidence high
    uint8_t _pad8[8];
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint64_t f_0x18;
    int32_t f_0x20;
    uint8_t _pad84[48];
    int32_t localPosition;  // named from setLocalPosition
    int32_t f_0x58;
    int32_t localScale;  // named from setLocalScale
    int32_t f_0x60;
    int32_t f_0x64;
    int32_t f_0x68;
    int32_t f_0x6c;
    uint8_t _pad116[4];
    float localAngle;  // named from setLocalAngle
    uint8_t _pad124[4];
    uint8_t worldPosition;  // named from getWorldPosition
    uint8_t worldScale;  // named from getWorldScale
    uint8_t worldAngle;  // named from getWorldAngle
    uint8_t _tail[1];
};

}  // namespace Walaber
#endif
