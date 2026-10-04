// Recovered from WaterConcept::NotificationSingleton. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__NOTIFICATIONSINGLETON_H
#define WMW_WATERCONCEPT__NOTIFICATIONSINGLETON_H

#include <stdint.h>

namespace WaterConcept {
struct NotificationSingleton {
    // size 320, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad32[24];
    uint64_t f_0x20;
    uint64_t f_0x28;
    uint8_t _pad56[8];
    uint64_t f_0x38;
    uint64_t f_0x40;
    uint8_t _pad80[8];
    uint64_t f_0x50;
    uint64_t f_0x58;
    uint64_t f_0x60;
    uint64_t f_0x68;
    uint8_t f_0x70;
    uint8_t _pad120[7];
    uint64_t f_0x78;
    uint64_t f_0x80;
    int32_t f_0x88;
    uint32_t f_0x8c;
    uint8_t _pad148[4];
    uint8_t f_0x94;
    uint8_t _pad256[107];
    uint64_t f_0x100;
    uint64_t f_0x108;
    float f_0x110;
    uint8_t _pad280[4];
    float f_0x118;
    uint8_t _pad288[4];
    double f_0x120;
    uint8_t _pad304[8];
    float f_0x130;
    uint8_t f_0x134;
    uint8_t _pad312[3];
    float f_0x138;
    uint8_t f_0x13c;
    uint8_t _tail[3];
};

}  // namespace WaterConcept
#endif
