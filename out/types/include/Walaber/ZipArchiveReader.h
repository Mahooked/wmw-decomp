// Recovered from Walaber::ZipArchiveReader. Offsets and element types are derived
// from load/store evidence in the binary; field names are not
// recorded anywhere in it.
#ifndef WMW_WALABER__ZIPARCHIVEREADER_H
#define WMW_WALABER__ZIPARCHIVEREADER_H

#include <stdint.h>

namespace Walaber {
struct ZipArchiveReader {
    // size 96, align 8, confidence high
    uint64_t f_0x0;
    uint64_t f_0x8;
    uint64_t f_0x10;
    uint8_t _pad88[64];
    int32_t f_0x58;
    uint8_t _tail[4];
};

}  // namespace Walaber
#endif
