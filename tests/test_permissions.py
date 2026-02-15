from src.ai_os.core.permissions import PermissionGateway


def test_permission_blocks_risky_ops_without_approval() -> None:
    gate = PermissionGateway(default_mode="admin", platform="windows")
    d = gate.evaluate("ops", "delete C:/important/data", approved_by_user=False)
    assert not d.allowed


def test_permission_allows_ops_with_approval() -> None:
    gate = PermissionGateway(default_mode="read", platform="windows")
    d = gate.evaluate("ops", "restart service", approved_by_user=True)
    assert d.allowed


def test_permission_blocks_rm_rf_bypass_case() -> None:
    gate = PermissionGateway(default_mode="admin", platform="unix")
    d = gate.evaluate("ops", "rm -rf /", approved_by_user=False)
    assert not d.allowed


def test_permission_blocks_windows_del_flags_bypass_case() -> None:
    gate = PermissionGateway(default_mode="admin", platform="windows")
    d = gate.evaluate("ops", "del /f /q C:/important/*", approved_by_user=False)
    assert not d.allowed


def test_permission_blocks_erase_obfuscation_case() -> None:
    gate = PermissionGateway(default_mode="admin", platform="windows")
    d = gate.evaluate("ops", "e r a s e C:/data", approved_by_user=False)
    assert not d.allowed


def test_permission_blocks_not_allowlisted_command_without_approval() -> None:
    gate = PermissionGateway(default_mode="admin", platform="windows")
    d = gate.evaluate("ops", "python cleanup.py", approved_by_user=False)
    assert not d.allowed
