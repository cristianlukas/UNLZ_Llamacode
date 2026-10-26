#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(__GNUC__)
#define FIXTURE_FN __attribute__((noinline, used))
#else
#define FIXTURE_FN
#endif

FIXTURE_FN int classify_command(uint8_t opcode, uint16_t length, uint8_t flags) {
    if (opcode == 0x10) {
        if (length > 64) return -2;
        return (flags & 1) ? 0x11 : 0x10;
    }
    if (opcode == 0x20) {
        if (length < 2 || length > 120) return -3;
        if ((flags & 3) == 3) return -4;
        return 0x20 + (flags & 3);
    }
    return -1;
}

FIXTURE_FN uint8_t transform_byte(uint8_t value, uint8_t index) {
    uint8_t key = (uint8_t)(index * 29u + 0x5bu);
    uint8_t mixed = (uint8_t)(value ^ key);
    unsigned shift = index & 7u;
    uint8_t rotated = shift == 0
        ? mixed
        : (uint8_t)((mixed << shift) | (mixed >> (8u - shift)));
    return (uint8_t)(rotated + 0x17u);
}

FIXTURE_FN uint16_t packet_crc16(const uint8_t *bytes, size_t length) {
    uint16_t crc = 0x6d3au;
    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)bytes[i] << 8;
        for (unsigned bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x8000u)
                ? (uint16_t)((crc << 1) ^ 0x1021u)
                : (uint16_t)(crc << 1);
        }
    }
    return (uint16_t)(crc ^ 0x6d3au);
}

FIXTURE_FN int next_state(uint8_t state, uint8_t event) {
    if (state == 0 && event == 1) return 1;
    if (state == 1 && event == 2) return 2;
    if (state == 1 && event == 3) return 0;
    if (state == 2 && event == 4) return 0;
    return -1;
}

static int parse_unsigned(const char *s, unsigned long max, unsigned long *out) {
    char *end = NULL;
    errno = 0;
    unsigned long value = strtoul(s, &end, 0);
    if (errno || end == s || *end != '\0' || value > max) return 0;
    *out = value;
    return 1;
}

static int run_transform(int argc, char **argv) {
    unsigned long value, index;
    if (argc != 4 || !parse_unsigned(argv[2], 255, &value) ||
        !parse_unsigned(argv[3], 255, &index)) return 2;
    printf("0x%02x\n", transform_byte((uint8_t)value, (uint8_t)index));
    return 0;
}

static int run_classify(int argc, char **argv) {
    unsigned long opcode, length, flags;
    if (argc != 5 || !parse_unsigned(argv[2], 255, &opcode) ||
        !parse_unsigned(argv[3], 65535, &length) ||
        !parse_unsigned(argv[4], 255, &flags)) return 2;
    printf("%d\n", classify_command((uint8_t)opcode, (uint16_t)length,
                                    (uint8_t)flags));
    return 0;
}

static int run_crc(int argc, char **argv) {
    uint8_t bytes[256];
    size_t count = 0;
    if (argc != 3 || (strlen(argv[2]) & 1u) || strlen(argv[2]) > 512) return 2;
    for (size_t i = 0; i < strlen(argv[2]); i += 2) {
        char pair[3] = {argv[2][i], argv[2][i + 1], '\0'};
        unsigned long value;
        if (!parse_unsigned(pair, 255, &value)) {
            char *end = NULL;
            errno = 0;
            value = strtoul(pair, &end, 16);
            if (errno || end != pair + 2 || value > 255) return 2;
        }
        bytes[count++] = (uint8_t)value;
    }
    printf("0x%04x\n", packet_crc16(bytes, count));
    return 0;
}

static int run_next(int argc, char **argv) {
    unsigned long state, event;
    if (argc != 4 || !parse_unsigned(argv[2], 255, &state) ||
        !parse_unsigned(argv[3], 255, &event)) return 2;
    printf("%d\n", next_state((uint8_t)state, (uint8_t)event));
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) return 2;
    if (strcmp(argv[1], "classify") == 0) return run_classify(argc, argv);
    if (strcmp(argv[1], "transform") == 0) return run_transform(argc, argv);
    if (strcmp(argv[1], "crc") == 0) return run_crc(argc, argv);
    if (strcmp(argv[1], "next") == 0) return run_next(argc, argv);
    return 2;
}
