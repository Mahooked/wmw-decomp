// Recovered from WaterConcept::GameState. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__GAMESTATE_H
#define WMW_WATERCONCEPT__GAMESTATE_H

#include <stdint.h>

namespace WaterConcept {
struct GameState {
    // size 472, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad24[8];
    uint64_t f_0x18;
    uint64_t f_0x20;
    uint8_t _pad48[8];
    uint64_t f_0x30;
    uint64_t f_0x38;
    uint8_t _pad72[8];
    uint64_t f_0x48;
    uint64_t f_0x50;
    uint8_t _pad96[8];
    uint64_t f_0x60;
    uint64_t f_0x68;
    uint8_t _pad120[8];
    uint64_t f_0x78;
    uint64_t f_0x80;
    uint8_t f_0x88;
    uint8_t f_0x89;
    uint8_t _pad140[2];
    int32_t f_0x8c;
    uint8_t f_0x90;
    uint8_t _pad148[3];
    int32_t f_0x94;
    uint8_t _pad168[16];
    uint64_t f_0xa8;
    uint8_t _pad184[8];
    uint64_t f_0xb8;
    uint8_t _pad200[8];
    uint64_t f_0xc8;
    uint8_t _pad220[12];
    float f_0xdc;
    float f_0xe0;
    int32_t f_0xe4;
    int32_t f_0xe8;
    uint8_t _pad240[4];
    uint64_t f_0xf0;
    uint64_t f_0xf8;
    uint8_t _pad288[32];
    uint64_t f_0x120;
    uint64_t f_0x128;
    uint8_t _pad336[32];
    int32_t f_0x150;
    int32_t f_0x154;
    int32_t f_0x158;
    uint8_t f_0x15c;
    uint8_t _pad352[3];
    uint8_t f_0x160;
    uint8_t f_0x161;
    uint8_t _pad356[2];
    int32_t f_0x164;
    int32_t f_0x168;
    uint8_t _pad368[4];
    uint64_t f_0x170;
    uint8_t _pad392[16];
    uint64_t f_0x188;
    uint64_t f_0x190;
    uint8_t _pad424[16];
    uint64_t f_0x1a8;
    uint8_t _pad468[36];
    int32_t f_0x1d4;
};

}  // namespace WaterConcept
#endif
