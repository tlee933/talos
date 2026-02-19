"""Tests for dangerous command detection."""

from talos.tui import is_dangerous


def test_rm_rf():
    assert is_dangerous("rm -rf /")
    assert is_dangerous("rm -rf /home/user")
    assert is_dangerous("sudo rm -rf /tmp/*")


def test_dd():
    assert is_dangerous("dd if=/dev/zero of=/dev/sda")
    assert is_dangerous("sudo dd if=image.iso of=/dev/sdb bs=4M")


def test_mkfs():
    assert is_dangerous("mkfs.ext4 /dev/sda1")
    assert is_dangerous("sudo mkfs -t xfs /dev/nvme0n1p1")


def test_fdisk():
    assert is_dangerous("fdisk /dev/sda")


def test_parted():
    assert is_dangerous("parted /dev/sda mklabel gpt")


def test_systemctl_stop():
    assert is_dangerous("systemctl stop sshd")
    assert is_dangerous("sudo systemctl stop NetworkManager")


def test_kill_9():
    assert is_dangerous("kill -9 1234")
    assert is_dangerous("sudo kill -9 $$")


def test_chmod_777():
    assert is_dangerous("chmod 777 /etc/passwd")


def test_dev_redirect():
    assert is_dangerous("cat something > /dev/sda")


def test_fork_bomb():
    assert is_dangerous(":(){ :|:& };:")


def test_safe_commands():
    """These should NOT be flagged as dangerous."""
    assert not is_dangerous("ls -la")
    assert not is_dangerous("cat /etc/hostname")
    assert not is_dangerous("echo hello")
    assert not is_dangerous("git status")
    assert not is_dangerous("python script.py")
    assert not is_dangerous("pip install requests")
    assert not is_dangerous("systemctl status sshd")
    assert not is_dangerous("rm file.txt")  # no -rf flag


def test_whitespace_handling():
    """Leading/trailing whitespace shouldn't affect detection."""
    assert is_dangerous("  rm -rf /  ")
    assert not is_dangerous("  ls -la  ")
