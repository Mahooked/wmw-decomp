// Recovered from Walaber::AchievementManager. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__ACHIEVEMENTMANAGER_H
#define WMW_WALABER__ACHIEVEMENTMANAGER_H

#include <stdint.h>

namespace Walaber {
struct AchievementManager {
    // size 152, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint64_t f_0x28;
    uint8_t f_0x30;
    uint8_t _pad56[7];
    uint64_t f_0x38;
    uint64_t f_0x40;
    int32_t f_0x48;
    uint8_t _pad80[4];
    uint8_t f_0x50;
    uint8_t _pad96[15];
    uint64_t f_0x60;
    int32_t f_0x68;
    uint8_t _pad112[4];
    uint64_t f_0x70;
    uint64_t f_0x78;
    uint64_t f_0x80;
    uint64_t f_0x88;
    uint64_t f_0x90;
};

}  // namespace Walaber
#endif
