#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <hivex.h>

static hive_node_h child_or_add(hive_h *h, hive_node_h parent, const char *name) {
    hive_node_h n = hivex_node_get_child(h, parent, name);
    if (n) return n;
    return hivex_node_add_child(h, parent, name);
}

static int set_ascii_string(hive_h *h, hive_node_h node, const char *key, const char *text) {
    size_t n = strlen(text);
    uint16_t *u16 = calloc(n + 1, sizeof(uint16_t));
    if (!u16) return -1;
    for (size_t i = 0; i < n; ++i) {
        if ((unsigned char)text[i] > 0x7f) { free(u16); errno = EILSEQ; return -1; }
        u16[i] = (uint16_t)(unsigned char)text[i];
    }
    hive_set_value v = {(char *)key, hive_t_REG_SZ, (n + 1) * sizeof(uint16_t), (char *)u16};
    int r = hivex_node_set_value(h, node, &v, 0);
    free(u16);
    return r;
}

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "usage: %s INPUT_HIVE OUTPUT_HIVE STRATA_ROOT CONFIG_PATH PROFILE_ID\n", argv[0]);
        return 2;
    }
    hive_h *h = hivex_open(argv[1], HIVEX_OPEN_WRITE);
    if (!h) { perror("hivex_open"); return 1; }
    hive_node_h n = hivex_root(h);
    const char *parts[] = {"Software", "LlamaCode", "LlamaCode"};
    for (size_t i = 0; i < sizeof(parts)/sizeof(parts[0]); ++i) {
        n = child_or_add(h, n, parts[i]);
        if (!n) { perror("create app settings key"); hivex_close(h); return 1; }
    }
    if (set_ascii_string(h, n, "LastLaunchId", argv[5]) < 0) {
        perror("set LastLaunchId"); hivex_close(h); return 1;
    }
    hive_node_h astra = child_or_add(h, n, "Astra");
    if (!astra) { perror("create Astra key"); hivex_close(h); return 1; }
    if (set_ascii_string(h, astra, "StrataRoot", argv[3]) < 0) {
        perror("set StrataRoot"); hivex_close(h); return 1;
    }
    hive_node_h config = child_or_add(h, astra, "ConfigFile");
    if (!config) { perror("create ConfigFile key"); hivex_close(h); return 1; }
    if (set_ascii_string(h, config, argv[5], argv[4]) < 0) {
        perror("set profile config path"); hivex_close(h); return 1;
    }
    if (hivex_commit(h, argv[2], 0) < 0) { perror("hivex_commit"); hivex_close(h); return 1; }
    if (hivex_close(h) < 0) { perror("hivex_close"); return 1; }
    puts("Updated LastLaunchId, Astra\\StrataRoot, and Astra\\ConfigFile profile value.");
    return 0;
}
