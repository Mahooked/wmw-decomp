// Recovered from Walaber::Widget_ProgressBar. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_PROGRESSBAR_H
#define WMW_WALABER__WIDGET_PROGRESSBAR_H

#include <stdint.h>

namespace Walaber {
struct Widget_ProgressBar {
    // size 376, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad144[136];
    float f_0x90;
    float f_0x94;
    uint8_t _pad256[104];
    uint64_t f_0x100;
    uint64_t f_0x108;
    uint64_t f_0x110;
    uint64_t f_0x118;
    double f_0x120;
    double f_0x128;
    double f_0x130;
    double f_0x138;
    float f_0x140;
    uint8_t _pad328[4];
    float f_0x148;
    uint8_t _pad336[4];
    float f_0x150;
    float f_0x154;
    uint8_t _pad352[8];
    float f_0x160;
    uint8_t _pad360[4];
    int32_t f_0x168;
    uint8_t f_0x16c;
    uint8_t f_0x16d;
    uint8_t f_0x16e;
    uint8_t f_0x16f;
    uint8_t f_0x170;
    uint8_t _tail[7];
};

}  // namespace Walaber
#endif
