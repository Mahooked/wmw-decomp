// Recovered from Walaber::FileManager. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__FILEMANAGER_H
#define WMW_WALABER__FILEMANAGER_H

#include <stdint.h>

namespace Walaber {
struct FileManager {
    // size 128, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint8_t _pad32[16];
    uint64_t f_0x20;
    uint8_t _pad56[16];
    uint64_t f_0x38;
    uint8_t _pad72[8];
    uint64_t f_0x48;
    uint64_t f_0x50;
    uint64_t f_0x58;
    uint64_t f_0x60;
    uint64_t f_0x68;
    uint64_t f_0x70;
    uint64_t f_0x78;
};

}  // namespace Walaber
#endif
