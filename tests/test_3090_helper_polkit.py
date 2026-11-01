#!/usr/bin/env python3
"""Static safety checks for the no-prompt, least-privilege Polkit action."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    policy_path, admin_path, installer_path, desktop_path, gui_path = map(Path, sys.argv[1:])
    policy = ET.parse(policy_path).getroot()
    action = policy.find("./action[@id='org.llamacode.3090-helper.repair']")
    require(action is not None, "missing dedicated repair action")

    defaults = action.find("defaults")
    require(defaults is not None, "missing action defaults")
    require(defaults.findtext("allow_active") == "yes", "active local session should not prompt")
    require(defaults.findtext("allow_any") == "no", "remote/any-session access must remain denied")
    require(defaults.findtext("allow_inactive") == "no", "inactive sessions must remain denied")

    annotations = {
        item.attrib.get("key"): item.text or ""
        for item in action.findall("annotate")
    }
    require(
        annotations.get("org.freedesktop.policykit.exec.path")
        == "@LC_3090_HELPER_ADMIN_PATH@",
        "Polkit must authorize only the fixed admin helper path",
    )
    require(
        annotations.get("org.freedesktop.policykit.exec.argv1") == "repair",
        "Polkit must authorize only the fixed repair subcommand",
    )
    require("allow_gui" not in annotations, "the privileged command must not inherit GUI environment")

    admin = admin_path.read_text(encoding="utf-8")
    require('case "${1:-}" in' in admin, "admin helper must dispatch through an allowlist")
    for command in ("repair)", "verify-boot)", "log)", "*)"):
        require(command in admin, f"missing explicit admin helper branch: {command}")
    require("eval " not in admin, "admin helper must not evaluate user-supplied shell text")

    installer = installer_path.read_text(encoding="utf-8")
    require("org.llamacode.3090-helper.policy.in" in installer, "installer must process the action template")
    require(
        "/usr/share/polkit-1/actions/org.llamacode.3090-helper.policy" in installer,
        "installer must install the policy in Polkit's action directory",
    )
    require("@LC_3090_HELPER_ADMIN_PATH@" in installer, "installer must bind the policy to its prefix")

    desktop = desktop_path.read_text(encoding="utf-8")
    require("Exec=/usr/local/bin/3090-helper" in desktop, "tray must launch as the session user")
    require("pkexec" not in desktop, "desktop startup must not run the GUI as root")
    gui = gui_path.read_text(encoding="utf-8")
    require('setProgram(QStringLiteral("/usr/bin/pkexec"))' in gui, "repair must use Polkit")
    require('QStringLiteral("repair")' in gui, "tray repair must request the fixed repair action")
    unlock_query = gui.split("const CommandResult unlockLog", 1)[1].split(
        "const CommandResult workerLog", 1
    )[0]
    require('QStringLiteral("--grep")' in unlock_query, "gpu-unlock evidence must be searched across the current boot")
    require('QStringLiteral("gpu_unlock: unlocked")' in unlock_query, "journal filter must select gpu-unlock success records")
    require('QStringLiteral("-n")' not in unlock_query, "boot-wide unlock evidence must not be truncated to recent lines")
    require("inputs.unlockKernelLog = unlockLog.output" in gui, "health check must consume the boot-wide unlock evidence")


if __name__ == "__main__":
    main()
