// Recovered from Walaber::Widget_ScoreCounter. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__WIDGET_SCORECOUNTER_H
#define WMW_WALABER__WIDGET_SCORECOUNTER_H

#include <stdint.h>

namespace Walaber {
struct Widget_ScoreCounter {
    // size 440, align 8, confidence high
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
    uint8_t _pad320[44];
    uint64_t f_0x140;
    uint64_t f_0x148;
    uint8_t _pad344[8];
    uint64_t f_0x158;
    uint64_t f_0x160;
    uint8_t _pad368[8];
    int32_t f_0x170;
    int32_t f_0x174;
    int32_t f_0x178;
    uint8_t f_0x17c;
    uint8_t f_0x17d;
    uint8_t f_0x17e;
    uint8_t f_0x17f;
    float f_0x180;
    float f_0x184;
    uint8_t _pad400[8];
    float f_0x190;
    int32_t f_0x194;
    int32_t f_0x198;
    int32_t f_0x19c;
    float f_0x1a0;
    int32_t f_0x1a4;
    uint8_t _pad432[8];
    int32_t f_0x1b0;
    uint8_t f_0x1b4;
    uint8_t _tail[3];
};

}  // namespace Walaber
#endif
