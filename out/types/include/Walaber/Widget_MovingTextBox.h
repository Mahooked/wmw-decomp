// Recovered from Walaber::Widget_MovingTextBox. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_MOVINGTEXTBOX_H
#define WMW_WALABER__WIDGET_MOVINGTEXTBOX_H

#include <stdint.h>

namespace Walaber {
struct Widget_MovingTextBox {
    // size 392, align 8, confidence high
    uint8_t f_0x0;
    uint8_t _pad144[143];
    double f_0x90;
    uint8_t _pad232[80];
    uint64_t f_0xe8;
    uint8_t _pad272[32];
    uint8_t f_0x110;
    uint8_t f_0x111;
    uint8_t f_0x112;
    uint8_t f_0x113;
    uint8_t _pad328[52];
    uint64_t f_0x148;
    uint64_t f_0x150;
    uint64_t f_0x158;
    uint8_t f_0x160;
    uint8_t f_0x161;
    uint8_t f_0x162;
    uint8_t f_0x163;
    float f_0x164;
    float f_0x168;
    uint8_t _pad372[8];
    float f_0x174;
    int32_t f_0x178;
    uint8_t _pad384[4];
    int32_t f_0x180;
    uint8_t f_0x184;
    uint8_t _tail[3];
};

}  // namespace Walaber
#endif
