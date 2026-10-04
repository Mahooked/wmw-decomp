// Recovered from WaterConcept::Spout. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WATERCONCEPT__SPOUT_H
#define WMW_WATERCONCEPT__SPOUT_H

#include <stdint.h>

namespace WaterConcept {
struct Spout {
    // size 1288, align 8, confidence high
    uint64_t f_0x0;
    uint8_t _pad274[266];
    uint8_t f_0x112;
    uint8_t _pad400[125];
    uint64_t f_0x190;
    uint8_t _pad680[272];
    int32_t f_0x2a8;
    uint8_t _pad800[116];
    uint64_t f_0x320;
    uint64_t f_0x328;
    uint8_t _pad936[120];
    double f_0x3a8;
    uint64_t f_0x3b0;
    uint64_t f_0x3b8;
    uint8_t _pad964[4];
    int32_t f_0x3c4;
    int32_t f_0x3c8;
    uint8_t _pad976[4];
    float f_0x3d0;
    int32_t f_0x3d4;
    uint64_t f_0x3d8;
    float f_0x3e0;
    float f_0x3e4;
    float f_0x3e8;
    float f_0x3ec;
    float f_0x3f0;
    int32_t f_0x3f4;
    uint8_t _pad1020[4];
    uint8_t f_0x3fc;
    uint8_t f_0x3fd;
    uint8_t f_0x3fe;
    uint8_t _pad1056[33];
    uint64_t f_0x420;
    uint64_t f_0x428;
    int32_t f_0x430;
    uint8_t _pad1080[4];
    uint64_t f_0x438;
    uint64_t f_0x440;
    uint8_t _pad1104[8];
    uint64_t f_0x450;
    uint64_t f_0x458;
    uint8_t _pad1128[8];
    float f_0x468;
    int32_t f_0x46c;
    int32_t f_0x470;
    uint8_t _pad1168[28];
    uint64_t f_0x490;
    uint8_t _pad1184[8];
    uint64_t f_0x4a0;
    uint64_t f_0x4a8;
    uint64_t f_0x4b0;
    int32_t f_0x4b8;
    uint8_t _pad1216[4];
    uint64_t f_0x4c0;
    uint64_t f_0x4c8;
    uint8_t _pad1236[4];
    uint8_t f_0x4d4;
    uint8_t f_0x4d5;
    uint8_t f_0x4d6;
    uint8_t _pad1240[1];
    uint8_t f_0x4d8;
    uint8_t _pad1256[15];
    uint64_t f_0x4e8;
    uint8_t f_0x4f0;
    uint8_t _pad1268[3];
    int32_t f_0x4f4;
    uint8_t _pad1276[4];
    uint8_t f_0x4fc;
    uint8_t _pad1280[3];
    float f_0x500;
    uint8_t f_0x504;
    uint8_t _tail[3];
};

}  // namespace WaterConcept
#endif
