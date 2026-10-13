# Build receipt

- Standard command: `./scripts/build-linux.sh Debug`
- Standard script result: stopped during its NTFS-to-cache `rsync` (exit 23) because it could not read pre-existing protected cache files under `artifacts/.../runtime/torch_compile/` and `artifacts/.../runtime/sol-docker-cache/torch_compile/`. No permissions or files in those directories were changed.
- Successful source mirror: `rsync -a --exclude='.git/' --exclude='.claude/' --exclude='build*/' --exclude='work/' --exclude='artifacts/' <repo>/ /home/cristian/.cache/llamacode/source/`
- Successful CMake configure: `cmake -S /home/cristian/.cache/llamacode/source -B /home/cristian/.cache/llamacode/build_linux -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_PREFIX_PATH=/home/cristian/Qt/6.8.3/gcc_64 -DBUILD_TESTS=OFF -DLC_USE_QTKEYCHAIN=ON`
- Successful build: `cmake --build /home/cristian/.cache/llamacode/build_linux --parallel 12` (exit 0; linked `LlamaCode`).
- The desktop launcher `/home/cristian/.local/bin/llamacode` selects `/home/cristian/.cache/llamacode/build_linux/LlamaCode` as its first executable candidate.
- No tests, inference, downloads, or GPU work were run for this profile-setting task.
