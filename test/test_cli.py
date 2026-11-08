import json
import socket

import pytest

from maglimit.cli import main


def test_scope_table(capsys):
    """Test the scope summary with eyepieces and a sky.
    """
    assert main(["scope", "--aperture", "200", "--fstop", "5",
                 "--eyepieces", "32,25,10", "--bortle", "5"]) == 0
    out = capsys.readouterr().out
    assert "200 mm f/5" in out
    assert "13.51" in out
    assert "31" in out and "6.4" in out
    assert "Bortle 5" in out


def test_scope_without_eyepieces_or_sky(capsys):
    """Test the minimum input still gives a useful summary.
    """
    assert main(["scope", "--aperture", "100", "--fstop", "4.5"]) == 0
    out = capsys.readouterr().out
    assert "Rule-of-thumb star limit: 12.00" in out
    assert "Eyepiece" not in out


def test_scope_json(capsys):
    """Test machine-readable output.
    """
    main(["scope", "--aperture", "200", "--fstop", "5", "--eyepieces", "32", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["eyepieces"][0]["magnification"] == pytest.approx(31.25)


@pytest.mark.parametrize("args", [
    ["--aperture", "200", "--fstop", "5", "--eyepieces", "32,,abc"],
    ["--aperture", "0", "--fstop", "5"],
    ["--aperture", "200", "--fstop", "5", "--bortle", "12"],
    ["--aperture", "nan", "--fstop", "5"],
    ["--aperture", "200", "--fstop", "5", "--eye-pupil", "0"],
    ["--aperture", "200", "--fstop", "5", "--eye-pupil", "70"],
])
def test_bad_input_exits_cleanly(args, capsys):
    """Test that bad values give a one-line error and exit code 2.
    """
    with pytest.raises(SystemExit) as exit_info:
        main(["scope", *args])
    assert exit_info.value.code == 2
    err = capsys.readouterr().err
    assert "error" in err and "Traceback" not in err


def test_scope_needs_no_network(monkeypatch, capsys):
    """Test that the scope command never connects to anything.
    """
    def no_network(*args, **kwargs):
        raise AssertionError("tried to use the network")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    assert main(["scope", "--aperture", "200", "--fstop", "5", "--bortle", "5"]) == 0


def test_no_command_shows_help(capsys):
    """Test that running with no command exits with a usage error.
    """
    with pytest.raises(SystemExit) as exit_info:
        main([])
    assert exit_info.value.code == 2


def test_check_prints_verdict(capsys):
    """Test the check command's text output.
    """
    assert main(["check", "M33", "--aperture", "200", "--fstop", "5", "--bortle", "7"]) == 0
    out = capsys.readouterr().out
    assert "M33" in out or "NGC 598" in out
    assert "Verdict:" in out and "mag/arcsec" in out


def test_check_shows_low_confidence(capsys):
    """Test that a nebula's answer is marked low confidence.
    """
    main(["check", "NGC 7000", "--aperture", "200", "--fstop", "5", "--bortle", "5"])
    assert "Low confidence" in capsys.readouterr().out


def test_check_json(capsys):
    """Test the check command's JSON output.
    """
    main(["check", "M57", "--aperture", "200", "--fstop", "5", "--sqm", "20", "--json"])
    assert json.loads(capsys.readouterr().out)["verdict"] == "easy"


@pytest.mark.parametrize("args", [
    ["M33", "--aperture", "200", "--fstop", "5"],
    ["M311", "--aperture", "200", "--fstop", "5", "--bortle", "5"],
])
def test_check_bad_input_exits_cleanly(args, capsys):
    """Test that a missing sky or an unknown object gives a clean error.
    """
    with pytest.raises(SystemExit) as exit_info:
        main(["check", *args])
    assert exit_info.value.code == 2
    assert "error" in capsys.readouterr().err


def test_check_needs_no_network(monkeypatch, capsys):
    """Test that check works without network access.
    """
    def no_network(*args, **kwargs):
        raise AssertionError("tried to use the network")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    assert main(["check", "M33", "--aperture", "200", "--fstop", "5", "--bortle", "7"]) == 0
